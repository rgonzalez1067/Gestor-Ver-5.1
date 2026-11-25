"""Pistas de Auditoría (audit_trails): interceptor transversal de escrituras MongoDB.

`AuditedDatabase` envuelve la base Motor; las colecciones de negocio/configuración
quedan envueltas por `AuditedCollection`, que registra CREATE/UPDATE/DELETE con
diff de campos. El módulo de Proyectos se excluye (usa su propia Bitácora).
"""
import contextvars
import logging
import re
from datetime import datetime, timezone, date

from bson import ObjectId

logger = logging.getLogger(__name__)

AUDIT_COLLECTION = "audit_trails"
RETENTION_DAYS = 730
MAX_DOCS_PER_OP = 500

COLLECTION_MODULES = {
    "quotes": "Cotizaciones", "quote_history": "Cotizaciones", "quote_custom_actions": "Cotizaciones",
    "quote_action_overrides": "Cotizaciones",
    "clients": "Clientes", "economic_groups": "Clientes", "brands": "Clientes", "initial_contacts": "Clientes", "client_documents": "Clientes",
    "banks": "Bancos", "banco_mediopago_condiciones": "Bancos",
    "services": "Medios de Pago",
    "exchange_rates": "Tasa de Cambio", "historico_tasas_cambio": "Tasa de Cambio",
    "hardware": "Bienes y Servicios", "component_types": "Bienes y Servicios",
    "fiscal_printer_models": "Bienes y Servicios", "servers": "Bienes y Servicios",
    "commercial_categories": "Categorías Comerciales",
    "referentes": "Referentes",
    "productos_integracion": "Productos para Integración",
    "integrators": "Integradores", "empresas_integradoras": "Integradores", "integrator_cert_templates": "Integradores", "integrator_certificates": "Integradores",
    "users": "Usuarios y Seguridad", "profiles": "Usuarios y Seguridad", "security_policies": "Usuarios y Seguridad",
    "config": "Configuración General", "email_templates": "Configuración General",
    "action_notification_configs": "Configuración General", "other_action_configs": "Configuración General",
    "notification_config": "Configuración General", "project_sla_config": "Configuración General",
    "project_sla_action_configs": "Configuración General", "holidays": "Configuración General",
    "message_templates": "Configuración General", "cc_groups": "Configuración General",
    "preferred_recipients": "Configuración General", "corporate_anexos": "Configuración General",
    "min_stock_config": "Inventario",
    "warehouses": "Inventario", "inventory_movements": "Inventario", "serial_assignments": "Inventario",
    "serial_blacklist": "Inventario", "temporary_assignments": "Inventario", "notas_entrega": "Inventario",
    "taller_equipos": "Taller",
    "new_products": "Nuevos Productos",
}
AUDIT_MODULES = sorted(set(COLLECTION_MODULES.values()))

EXCLUDED_PATH_PREFIXES = ("/api/projects", "/api/direct-projects")

# Campos técnicos que, si son los únicos alterados, no generan pista.
NOISE_FIELDS = {"updated_at", "last_login", "last_login_at", "last_activity", "last_activity_at", "last_seen",
                "last_seen_at", "is_online", "online", "failed_login_attempts", "_id"}
_SENSITIVE_EXACT = {"password", "passwd", "password_hash", "hashed_password", "new_password", "old_password",
                    "current_password", "smtp_password", "token", "secret", "client_secret", "api_key", "apikey",
                    "otp", "otp_code", "otp_hash", "code_hash"}


class _SensitiveMatcher:
    """Coincidencia por nombre exacto del campo (último segmento de la ruta)."""

    @staticmethod
    def search(key: str) -> bool:
        k = re.split(r"[.\[\]]", str(key).strip("]"))[-1].lower() if key else ""
        return k in _SENSITIVE_EXACT or k.endswith(("_token", "_secret", "_api_key", "password_hash"))


SENSITIVE_RE = _SensitiveMatcher()

# Identificador legible por colección (primer campo presente).
ID_FIELDS = {
    "quotes": ("quote_number", "quote_id"), "quote_history": ("quote_number", "history_id", "quote_id"),
    "clients": ("rif", "client_id"), "brands": ("name", "brand_id"), "banks": ("name", "bank_id"), "users": ("email", "user_id"),
    "services": ("name", "service_id"), "integrators": ("rif", "name", "integrator_id"),
    "empresas_integradoras": ("rif", "razon_social", "empresa_id"),
    "referentes": ("nombre_referente", "referente_id"),
    "productos_integracion": ("nombre", "producto_id"),
    "security_policies": ("policy_id",), "hardware": ("name", "hardware_id"),
}
GENERIC_ID_FIELDS = ("quote_number", "rif", "email", "code", "name", "nombre", "key", "id")

_ctx = contextvars.ContextVar("audit_ctx", default=None)


def new_request_context(ip: str, user_agent: str, endpoint: str, method: str) -> dict:
    ctx = {"ip": ip, "user_agent": user_agent, "endpoint": endpoint, "method": method, "user": None}
    _ctx.set(ctx)
    return ctx


def set_audit_user(user: dict):
    ctx = _ctx.get()
    if ctx is not None and user:
        ctx["user"] = {"user_id": user.get("user_id"), "email": user.get("email", ""),
                       "name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or user.get("name", "")}


def _jsonable(v):
    if isinstance(v, ObjectId):
        return str(v)
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, bytes):
        return f"<{len(v)} bytes>"
    if isinstance(v, dict):
        return {str(k): _jsonable(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_jsonable(x) for x in v]
    return v


def _mask(v, key=""):
    if key and SENSITIVE_RE.search(key):
        return "***"
    if isinstance(v, dict):
        return {k: _mask(x, k) for k, x in v.items()}
    if isinstance(v, list):
        return [_mask(x) for x in v]
    return v


def _clean(doc):
    if not doc:
        return doc
    d = {k: v for k, v in doc.items() if k != "_id"}
    return _mask(_jsonable(d))


_LIST_KEYS = ("integration_id", "id", "item_id", "service_id", "bank_id", "client_id", "user_id", "contact_id", "key")


def _list_key(items):
    if not items or not all(isinstance(x, dict) for x in items):
        return None
    for k in _LIST_KEYS:
        if all(k in x for x in items):
            return k
    return None


def _diff(before, after, path="", out=None):
    """Diff profundo: {ruta: (antes, despues)}; listas de dicts se emparejan por id."""
    if out is None:
        out = {}
    if isinstance(before, dict) and isinstance(after, dict):
        for k in set(before) | set(after):
            if not path and k in ("_id",):
                continue
            _diff(before.get(k), after.get(k), f"{path}.{k}" if path else k, out)
        return out
    if isinstance(before, list) and isinstance(after, list):
        lk = _list_key(before + after)
        if lk:
            bmap = {str(x[lk]): x for x in before}
            amap = {str(x[lk]): x for x in after}
            for key in list(bmap) + [k for k in amap if k not in bmap]:
                _diff(bmap.get(key), amap.get(key), f"{path}[{key}]", out)
            return out
    if before != after:
        out[path] = (before, after)
    return out


def _registro_id(coll: str, doc: dict) -> str:
    for f in ID_FIELDS.get(coll, ()) + tuple(k for k in doc if k.endswith("_id")) + GENERIC_ID_FIELDS:
        if doc.get(f):
            return str(doc[f])
    return str(doc.get("_id", ""))


def _entity_id(coll: str, doc: dict) -> str:
    for k in doc:
        if k.endswith("_id") and k not in ("created_by_user_id",) and isinstance(doc[k], str):
            return doc[k]
    return str(doc.get("_id", ""))


class AuditedCollection:
    def __init__(self, coll, raw_db):
        self._coll = coll
        self._raw_db = raw_db
        self._name = coll.name

    def __getattr__(self, name):
        return getattr(self._coll, name)

    def __getitem__(self, name):
        return self._coll[name]

    def _skip(self):
        ctx = _ctx.get()
        return bool(ctx and (ctx.get("endpoint") or "").startswith(EXCLUDED_PATH_PREFIXES))

    async def _log(self, accion, before=None, after=None):
        try:
            ctx = _ctx.get() or {}
            user = ctx.get("user") or {}
            if ctx and not user:
                nombre, email = "Anónimo", ""
            elif not ctx:
                nombre, email = "Sistema", "sistema"
            else:
                nombre, email = user.get("name") or user.get("email"), user.get("email", "")
            ref = after if after is not None else before
            if accion == "UPDATE":
                d = _diff(_jsonable(before), _jsonable(after))
                d = {k: v for k, v in d.items() if k.split(".")[0].split("[")[0] not in NOISE_FIELDS}
                if not d:
                    return
                campos = sorted(d)
                prev = _mask({k: v[0] for k, v in d.items()})
                new = _mask({k: v[1] for k, v in d.items()})
                prev = {k: ("***" if SENSITIVE_RE.search(k) else v) for k, v in prev.items()}
                new = {k: ("***" if SENSITIVE_RE.search(k) else v) for k, v in new.items()}
            elif accion == "CREATE":
                prev, new = None, _clean(after)
                campos = sorted(new.keys())
            else:
                prev, new, campos = _clean(before), None, None
            await self._raw_db[AUDIT_COLLECTION].insert_one({
                "modulo": COLLECTION_MODULES.get(self._name, self._name),
                "entidad": self._name,
                "registro_id": _registro_id(self._name, ref),
                "entidad_id": _entity_id(self._name, ref),
                "accion": accion,
                "valores_anteriores": prev,
                "valores_nuevos": new,
                "campos_modificados": campos,
                "usuario_id": user.get("user_id") or ("system" if not ctx else None),
                "usuario_nombre": nombre,
                "usuario_email": email,
                "ip_origen": ctx.get("ip", ""),
                "user_agent": ctx.get("user_agent", ""),
                "endpoint": f"{ctx.get('method', '')} {ctx.get('endpoint', '')}".strip() or "proceso interno",
                "fecha_hora": datetime.now(timezone.utc),
            })
        except Exception as e:
            logger.warning(f"[audit_trail] no se pudo registrar {accion} en {self._name}: {e}")

    async def _before_many(self, flt, session=None):
        return await self._coll.find(flt, session=session).to_list(MAX_DOCS_PER_OP)

    async def _after_by_ids(self, ids, session=None):
        docs = await self._coll.find({"_id": {"$in": ids}}, session=session).to_list(len(ids) or 1)
        return {d["_id"]: d for d in docs}

    # ---------- INSERT ----------
    async def insert_one(self, document, *args, **kwargs):
        res = await self._coll.insert_one(document, *args, **kwargs)
        if not self._skip():
            await self._log("CREATE", after=document)
        return res

    async def insert_many(self, documents, *args, **kwargs):
        documents = list(documents)
        res = await self._coll.insert_many(documents, *args, **kwargs)
        if not self._skip():
            for d in documents[:MAX_DOCS_PER_OP]:
                await self._log("CREATE", after=d)
        return res

    # ---------- UPDATE ----------
    async def _update_generic(self, op, flt, args, kwargs, many=False):
        if self._skip():
            return await op(flt, *args, **kwargs)
        session = kwargs.get("session")
        if many:
            befores = await self._before_many(flt, session)
        else:
            b = await self._coll.find_one(flt, sort=kwargs.get("sort"), session=session)
            befores = [b] if b else []
        res = await op(flt, *args, **kwargs)
        afters = await self._after_by_ids([b["_id"] for b in befores], session) if befores else {}
        for b in befores:
            a = afters.get(b["_id"])
            if a is None:
                await self._log("DELETE", before=b)
            else:
                await self._log("UPDATE", before=b, after=a)
        if not befores and kwargs.get("upsert"):
            upserted = getattr(res, "upserted_id", None)
            doc = await self._coll.find_one({"_id": upserted} if upserted is not None else flt, session=session)
            if doc:
                await self._log("CREATE", after=doc)
        return res

    async def update_one(self, flt, *args, **kwargs):
        return await self._update_generic(self._coll.update_one, flt, args, kwargs)

    async def update_many(self, flt, *args, **kwargs):
        return await self._update_generic(self._coll.update_many, flt, args, kwargs, many=True)

    async def replace_one(self, flt, *args, **kwargs):
        return await self._update_generic(self._coll.replace_one, flt, args, kwargs)

    async def find_one_and_update(self, flt, *args, **kwargs):
        return await self._update_generic(self._coll.find_one_and_update, flt, args, kwargs)

    async def find_one_and_replace(self, flt, *args, **kwargs):
        return await self._update_generic(self._coll.find_one_and_replace, flt, args, kwargs)

    # ---------- DELETE ----------
    async def delete_one(self, flt, *args, **kwargs):
        if self._skip():
            return await self._coll.delete_one(flt, *args, **kwargs)
        b = await self._coll.find_one(flt, session=kwargs.get("session"))
        res = await self._coll.delete_one(flt, *args, **kwargs)
        if b and getattr(res, "deleted_count", 0):
            await self._log("DELETE", before=b)
        return res

    async def delete_many(self, flt, *args, **kwargs):
        if self._skip():
            return await self._coll.delete_many(flt, *args, **kwargs)
        befores = await self._before_many(flt, kwargs.get("session"))
        res = await self._coll.delete_many(flt, *args, **kwargs)
        for b in befores:
            await self._log("DELETE", before=b)
        return res

    async def find_one_and_delete(self, flt, *args, **kwargs):
        res = await self._coll.find_one_and_delete(flt, *args, **kwargs)
        if res and not self._skip():
            await self._log("DELETE", before=res)
        return res


class AuditedDatabase:
    """Proxy de AsyncIOMotorDatabase: envuelve solo las colecciones auditadas."""

    def __init__(self, raw_db):
        object.__setattr__(self, "_db", raw_db)
        object.__setattr__(self, "_cache", {})

    def _wrap(self, name, coll):
        if name not in COLLECTION_MODULES:
            return coll
        cache = self._cache
        if name not in cache:
            cache[name] = AuditedCollection(coll, self._db)
        return cache[name]

    def __getattr__(self, name):
        attr = getattr(self._db, name)
        if name in COLLECTION_MODULES:
            return self._wrap(name, attr)
        return attr

    def __getitem__(self, name):
        return self._wrap(name, self._db[name])

    def get_collection(self, name, *args, **kwargs):
        return self._wrap(name, self._db.get_collection(name, *args, **kwargs))

    @property
    def raw(self):
        return self._db


async def ensure_audit_indexes(raw_db):
    c = raw_db[AUDIT_COLLECTION]
    await c.create_index("fecha_hora", expireAfterSeconds=RETENTION_DAYS * 86400, name="ttl_fecha_hora")
    for idx in (["modulo", "entidad"], ["registro_id"], ["entidad_id"], ["usuario_email"], ["accion"], ["campos_modificados"]):
        await c.create_index([(f, 1) for f in idx])


class AuditContextMiddleware:
    """ASGI puro: crea el contexto (IP, User-Agent, endpoint) de cada petición."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        headers = {k.decode().lower(): v.decode(errors="ignore") for k, v in scope.get("headers", [])}
        ip = (headers.get("x-forwarded-for") or "").split(",")[0].strip() or headers.get("x-real-ip") or (scope.get("client") or ("",))[0]
        new_request_context(ip, headers.get("user-agent", ""), scope.get("path", ""), scope.get("method", ""))
        return await self.app(scope, receive, send)
