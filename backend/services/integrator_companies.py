"""Jerarquía Empresa Integradora (padre) → Aplicativos/Integraciones (db.integrators, hijos)."""
import re
import uuid
import unicodedata
from datetime import datetime, timezone

from config import db

COLL = "empresas_integradoras"
LEGAL = r'\b(c ?a|s ?a|s ?r ?l|s ?a ?s|inc|llc|corp|ltd|cia|compania|grupo)\b'
RIF_RE = re.compile(r'^([VEJGPC])-?(\d{8})-?(\d)$')
EMAIL_RE = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')


def _base(s):
    s = unicodedata.normalize('NFKD', str(s or '')).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', ' ', s)


def norm_company(s):
    n = re.sub(r'\s+', ' ', re.sub(LEGAL, ' ', _base(s))).strip()
    return n or _base(s).strip()


def clean_name(s):
    return re.sub(r'\s+', ' ', str(s or '')).strip()


def normalize_rif(rif):
    m = RIF_RE.match(re.sub(r'[\s.]', '', str(rif or '')).upper())
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else None


def is_incomplete(e):
    contacts = [c for c in (e.get("contacts") or []) if (c.get("full_name") or "").strip()]
    return not (e.get("rif") and (e.get("direccion_fiscal") or "").strip() and contacts)


def _new_company(razon_social, contacts):
    return {
        "empresa_id": f"emp_{uuid.uuid4().hex[:12]}",
        "tipo_persona": "Jurídica",
        "razon_social": razon_social,
        "norm_name": norm_company(razon_social),
        "rif": None,
        "direccion_fiscal": "",
        "rif_document_url": None,
        "rif_document_filename": None,
        "contacts": contacts,
        "migrated": True,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _principal_contact(row):
    name = clean_name(row.get("principal_contact_name"))
    email = (row.get("principal_contact_email") or "").strip()
    if not name and email:
        name = next((c.get("name") for c in (row.get("contacts") or []) if (c.get("email") or "").strip().lower() == email.lower()), "") or email
    if not name:
        return None
    return {"contact_id": f"ctc_{uuid.uuid4().hex[:8]}", "full_name": name, "phone": (row.get("principal_contact_phone") or "").strip(),
            "email": email, "role": "Contacto Principal"}


async def link_orphan_integrators():
    """Vincula cada aplicativo sin empresa a su Empresa Integradora (crea la empresa si no existe)."""
    orphans = await db.integrators.find(
        {"$or": [{"empresa_integradora_id": {"$exists": False}}, {"empresa_integradora_id": None}, {"empresa_integradora_id": ""}]},
        {"_id": 0},
    ).to_list(None)
    if not orphans:
        return 0
    by_norm = {e["norm_name"]: e async for e in db[COLL].find({}, {"_id": 0, "empresa_id": 1, "norm_name": 1, "razon_social": 1})}
    groups = {}
    for r in orphans:
        groups.setdefault(norm_company(r.get("name")), []).append(r)
    for key, rows in groups.items():
        company = by_norm.get(key)
        if not company:
            razon = max((clean_name(r.get("name")) for r in rows), key=len) or "Sin nombre"
            contacts, seen = [], set()
            for r in rows:
                c = _principal_contact(r)
                k = (c or {}).get("email", "").lower() or (c or {}).get("full_name", "").lower()
                if c and k not in seen:
                    seen.add(k)
                    contacts.append(c)
            company = _new_company(razon, contacts)
            await db[COLL].insert_one(dict(company))
            by_norm[key] = company
        await db.integrators.update_many(
            {"integrator_id": {"$in": [r["integrator_id"] for r in rows]}},
            {"$set": {"empresa_integradora_id": company["empresa_id"], "name": company["razon_social"]}},
        )
    return len(orphans)


async def remember_technicians(integrator_id, techs):
    """Suma los técnicos del proyecto al directorio del aplicativo (dedupe por email o nombre)."""
    if not integrator_id or not techs:
        return
    intg = await db.integrators.find_one({"integrator_id": integrator_id}, {"_id": 0, "contacts": 1})
    if not intg:
        return
    merged = list(intg.get("contacts") or [])
    keys = {((c.get("email") or "").strip().lower() or (c.get("name") or "").strip().lower()) for c in merged}
    changed = False
    for t in techs:
        k = (t.get("email") or "").strip().lower() or (t.get("name") or "").strip().lower()
        if k and k not in keys:
            keys.add(k)
            merged.append({"contact_id": f"ctc_{uuid.uuid4().hex[:8]}", "name": t.get("name"), "email": t.get("email") or None,
                           "phone": t.get("phone") or None, "role": t.get("role") or None})
            changed = True
    if changed:
        await db.integrators.update_one({"integrator_id": integrator_id}, {"$set": {"contacts": merged}})


def clean_technicians(techs):
    out = []
    for t in techs or []:
        name = clean_name(t.get("name"))
        if not name:
            continue
        email = (t.get("email") or "").strip()
        if email and not EMAIL_RE.match(email):
            raise ValueError(f"Email inválido para el técnico {name}")
        out.append({"tech_id": t.get("tech_id") or f"tec_{uuid.uuid4().hex[:8]}", "name": name,
                    "phone": (t.get("phone") or "").strip(), "email": email, "role": (t.get("role") or "").strip()})
    return out
