"""Routes: /api/productos-integracion — Catálogo maestro de Productos para Integración (Matriz del Integrador)."""
import re
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from config import db, get_current_user
from routes import integrators as intg_mod

router = APIRouter(tags=["productos-integracion"])
ALL_PRODUCT_NAMES: dict = {}


class ProductoIn(BaseModel):
    codigo: str = Field(..., min_length=1, max_length=30)
    nombre: str = Field(..., min_length=1, max_length=150)
    descripcion: Optional[str] = ""
    orden_despliegue: Optional[int] = None
    activo: bool = True


class ProductoUpdate(BaseModel):
    codigo: Optional[str] = Field(None, min_length=1, max_length=30)
    nombre: Optional[str] = Field(None, min_length=1, max_length=150)
    descripcion: Optional[str] = None
    orden_despliegue: Optional[int] = None
    activo: Optional[bool] = None


def _code(v: str) -> str:
    return re.sub(r"\s+", "_", v.strip()).upper()


async def refresh_products():
    """Recarga en caliente la lista de productos usada por la Matriz, exportaciones y certificados."""
    docs = await db.productos_integracion.find({}, {"_id": 0}).to_list(2000)
    if not docs:
        return
    docs.sort(key=lambda d: (d.get("orden_despliegue") if d.get("orden_despliegue") is not None else 10**6, d["nombre"].casefold()))
    active = [{"id": d["producto_id"], "name": d["nombre"]} for d in docs if d.get("activo", True)]
    intg_mod.INTEGRATOR_PRODUCTS[:] = active
    intg_mod.INTEGRATOR_PRODUCT_IDS[:] = [p["id"] for p in active]
    intg_mod.INTEGRATOR_PRODUCT_NAME_TO_ID.clear()
    intg_mod.INTEGRATOR_PRODUCT_NAME_TO_ID.update({p["name"].lower().strip(): p["id"] for p in active})
    ALL_PRODUCT_NAMES.clear()
    ALL_PRODUCT_NAMES.update({d["producto_id"]: d["nombre"] for d in docs})


async def seed_products_and_baselines():
    """Idempotente: siembra los productos fijos históricos y la línea base de certificación."""
    if not await db.productos_integracion.count_documents({}):
        now = datetime.now(timezone.utc).isoformat()
        await db.productos_integracion.insert_many([{
            "producto_id": p["id"], "codigo": _code(p["id"].removeprefix("prod_")), "nombre": p["name"],
            "descripcion": "", "orden_despliegue": (i + 1) * 10, "activo": True, "created_at": now, "created_by": "sistema",
        } for i, p in enumerate(intg_mod.INTEGRATOR_PRODUCTS)])
    if not await db["_migrations"].find_one({"_id": "cert_baseline_v1"}):
        with_cert = set(await db.integrator_certificates.distinct("integrator_id", {"status": {"$ne": "anulado"}}))
        async for i in db.integrators.find({"integrator_id": {"$in": list(with_cert)}}, {"_id": 0, "integrator_id": 1, "certifications": 1}):
            base = [k for k, v in (i.get("certifications") or {}).items() if str(v).strip().upper() == "C"]
            await db.integrators.update_one({"integrator_id": i["integrator_id"]}, {"$set": {"cert_baseline": base}})
        await db["_migrations"].insert_one({"_id": "cert_baseline_v1", "ran_at": datetime.now(timezone.utc).isoformat()})
    await refresh_products()


async def _require_admin(authorization):
    user = await get_current_user(authorization)
    if (user.get("role") or "").lower() != "admin":
        raise HTTPException(status_code=403, detail="Solo el Administrador puede mantener este catálogo")
    return user


@router.get("/productos-integracion")
async def list_productos(authorization: Optional[str] = Header(None)):
    await _require_admin(authorization)
    docs = await db.productos_integracion.find({}, {"_id": 0}).to_list(2000)
    usage = {"C": {}, "P": {}}
    async for i in db.integrators.find({}, {"_id": 0, "certifications": 1}):
        for k, v in (i.get("certifications") or {}).items():
            st = str(v).strip().upper()
            if st in usage:
                usage[st][k] = usage[st].get(k, 0) + 1
    for d in docs:
        d["certificados"] = usage["C"].get(d["producto_id"], 0)
        d["en_proceso"] = usage["P"].get(d["producto_id"], 0)
        d["aplicativos"] = d["certificados"] + d["en_proceso"]
    docs.sort(key=lambda d: (d.get("orden_despliegue") if d.get("orden_despliegue") is not None else 10**6, d["nombre"].casefold()))
    return docs


async def _check_unique(codigo: Optional[str], nombre: Optional[str], exclude: str = ""):
    q = {"producto_id": {"$ne": exclude}}
    if codigo and await db.productos_integracion.find_one({**q, "codigo": _code(codigo)}, {"_id": 1}):
        raise HTTPException(status_code=409, detail="Ya existe un producto con ese código")
    if nombre and await db.productos_integracion.find_one({**q, "nombre": {"$regex": f"^{re.escape(nombre.strip())}$", "$options": "i"}}, {"_id": 1}):
        raise HTTPException(status_code=409, detail="Ya existe un producto con ese nombre")


@router.post("/productos-integracion")
async def create_producto(data: ProductoIn, authorization: Optional[str] = Header(None)):
    user = await _require_admin(authorization)
    await _check_unique(data.codigo, data.nombre)
    doc = {"producto_id": f"prod_{uuid.uuid4().hex[:10]}", "codigo": _code(data.codigo), "nombre": data.nombre.strip(),
           "descripcion": (data.descripcion or "").strip(), "orden_despliegue": data.orden_despliegue, "activo": data.activo,
           "created_at": datetime.now(timezone.utc).isoformat(), "created_by": user.get("email", "")}
    await db.productos_integracion.insert_one(doc)
    doc.pop("_id", None)
    await refresh_products()
    return doc


@router.put("/productos-integracion/{producto_id}")
async def update_producto(producto_id: str, data: ProductoUpdate, authorization: Optional[str] = Header(None)):
    await _require_admin(authorization)
    if not await db.productos_integracion.find_one({"producto_id": producto_id}, {"_id": 1}):
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    upd = data.model_dump(exclude_unset=True)
    await _check_unique(upd.get("codigo"), upd.get("nombre"), producto_id)
    if "codigo" in upd:
        upd["codigo"] = _code(upd["codigo"])
    if "nombre" in upd:
        upd["nombre"] = upd["nombre"].strip()
    upd["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.productos_integracion.update_one({"producto_id": producto_id}, {"$set": upd})
    await refresh_products()
    return await db.productos_integracion.find_one({"producto_id": producto_id}, {"_id": 0})


@router.delete("/productos-integracion/{producto_id}")
async def delete_producto(producto_id: str, authorization: Optional[str] = Header(None)):
    """Elimina el producto del catálogo. Los certificados ya emitidos conservan el nombre en su histórico."""
    await _require_admin(authorization)
    doc = await db.productos_integracion.find_one({"producto_id": producto_id}, {"_id": 0, "nombre": 1})
    if not doc:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    if await db.productos_integracion.count_documents({"activo": {"$ne": False}, "producto_id": {"$ne": producto_id}}) == 0:
        raise HTTPException(status_code=400, detail="Debe quedar al menos un producto activo en el catálogo")
    await db.productos_integracion.delete_one({"producto_id": producto_id})
    await refresh_products()
    return {"ok": True, "message": f"Producto «{doc['nombre']}» eliminado"}


async def _apps_with_product(producto_id: str) -> list:
    apps = await db.integrators.find(
        {f"certifications.{producto_id}": {"$regex": r"^\s*[cC]\s*$"}},
        {"_id": 0, "integrator_id": 1, "name": 1, "app_name": 1, "integration_type": 1, "implementador": 1, "integrator_status": 1},
    ).to_list(5000)
    apps.sort(key=lambda a: ((a.get("name") or "").casefold(), (a.get("app_name") or "").casefold()))
    return apps


@router.get("/productos-integracion/{producto_id}/certificados")
async def productos_certificados(producto_id: str, authorization: Optional[str] = Header(None)):
    await _require_admin(authorization)
    return await _apps_with_product(producto_id)


@router.get("/productos-integracion/{producto_id}/certificados/pdf")
async def productos_certificados_pdf(producto_id: str, authorization: Optional[str] = Header(None)):
    from fastapi.responses import StreamingResponse
    from services.pdf_report import build_corporate_pdf
    await _require_admin(authorization)
    prod = await db.productos_integracion.find_one({"producto_id": producto_id}, {"_id": 0, "nombre": 1, "codigo": 1})
    if not prod:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    apps = await _apps_with_product(producto_id)
    rows = [[i + 1, a.get("name") or "", a.get("app_name") or "", a.get("integration_type") or "", a.get("implementador") or "", a.get("integrator_status") or ""]
            for i, a in enumerate(apps)]
    buf = build_corporate_pdf(
        f"Integradores con «{prod['nombre']}» Certificado ({len(apps)})",
        ["#", "Integrador", "Aplicativo", "Tipo de Integración", "Implementador", "Estatus"], rows,
        col_ratios=[0.05, 0.3, 0.22, 0.13, 0.17, 0.13])
    fname = f"Certificados_{prod['codigo']}_{datetime.now(timezone.utc).strftime('%Y%m%d')}.pdf"
    return StreamingResponse(buf, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{fname}"'})
