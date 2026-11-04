"""Edición Maestra: gestión de sucursales, RIFs y medios de pago con topes
contractuales (cajas totales y cajas por medio de pago)."""
import uuid
from fastapi import HTTPException

from config import db


def _key(bank: str, product: str) -> str:
    return f"{(bank or '').strip()}|{(product or '').strip()}"


def compute_baseline(project: dict) -> dict:
    """Topes contratados: total de cajas y cajas por medio (banco|producto).
    Se congela en el proyecto la primera vez que se guardan sucursales."""
    if project.get("contract_baseline"):
        return project["contract_baseline"]
    total = int(project.get("box_count") or project.get("cantidad_cajas") or 0)
    medios = {}
    for s in project.get("services") or []:
        if s.get("item_type") != "additional":
            continue
        k = _key(s.get("bank_name"), s.get("item_name"))
        cap = int(s.get("cantidad_cajas") or s.get("quantity") or total or 0)
        medios[k] = max(medios.get(k, 0), cap)
    if not medios:
        for bn, prods in (project.get("implementation_matrix") or {}).items():
            for pn in (prods or {}):
                medios[_key(bn, pn)] = total
    if not total:
        total = sum(int(st.get("box_count") or 0) for st in project.get("stores") or [])
    return {"total_boxes": total, "medios": medios}


def is_store_certified(store: dict) -> bool:
    """Certificada = todos sus medios completaron la fase 'En Producción'."""
    phases = [ph for prods in (store.get("implementation_matrix") or {}).values() for ph in (prods or {}).values()]
    return bool(phases) and all(((ph or {}).get("En Producción") or {}).get("completed") for ph in phases)


async def eligible_rif_clients(project: dict) -> list:
    ids = {r.get("client_id") for r in project.get("rifs") or [] if r.get("client_id")}
    if project.get("client_id"):
        ids.add(project["client_id"])
    base = await db.clients.find({"client_id": {"$in": list(ids)}}, {"_id": 0, "grupo_economico": 1}).to_list(200)
    groups = {(c.get("grupo_economico") or "").strip() for c in base} - {""}
    query = {"$or": [{"client_id": {"$in": list(ids)}}] + ([{"grupo_economico": {"$in": list(groups)}}] if groups else [])}
    return await db.clients.find(
        query, {"_id": 0, "client_id": 1, "rif": 1, "legal_name": 1, "fantasy_name": 1, "grupo_economico": 1}
    ).sort("legal_name", 1).to_list(500)


def _fail(msg: str):
    raise HTTPException(status_code=400, detail=msg)


async def apply_branches(project: dict, branches: list, replacements: list, build_matrix) -> dict:
    """Valida y reconstruye stores/rifs/matriz. Devuelve el dict de update."""
    baseline = compute_baseline(project)
    caps = dict(baseline["medios"])

    # Reemplazos: el medio nuevo hereda (comparte) el tope del medio cotizado que reemplaza.
    group_of = {k: k for k in caps}
    for r in replacements or []:
        old_k, new_k = _key(r.bank_name, r.from_product), _key(r.bank_name, r.to_product)
        if old_k not in caps:
            _fail(f"Reemplazo inválido: «{r.from_product}» ({r.bank_name}) no está en la cotización original.")
        if new_k in caps:
            continue
        group_of[new_k] = group_of[old_k]

    total = sum(int(b.box_count or 0) for b in branches)
    if total > baseline["total_boxes"]:
        _fail(f"Límite Excedido: La sumatoria de cajas asignadas ({total}) supera el tope máximo de cajas contratadas en el proyecto ({baseline['total_boxes']}).")

    used = {}
    for b in branches:
        if int(b.box_count or 0) < 0:
            _fail("La cantidad de cajas no puede ser negativa.")
        for m in b.medios:
            k = _key(m.bank_name, m.product_name)
            if k not in group_of:
                _fail(f"Producto no contratado: «{m.product_name}» ({m.bank_name}) no forma parte de la cotización original.")
            g = group_of[k]
            used[g] = used.get(g, 0) + int(b.box_count or 0)
    for g, n in used.items():
        if n > caps[g]:
            bank, prod = g.split("|", 1)
            _fail(f"Límite Excedido: el medio de pago «{prod}» ({bank}) tiene {n} cajas asignadas y su tope contratado es {caps[g]}.")

    # RIFs: existentes del proyecto o clientes del mismo cliente/grupo económico.
    rifs = {r.get("rif_id"): dict(r) for r in project.get("rifs") or []}
    eligible = {c["client_id"]: c for c in await eligible_rif_clients(project)}
    by_client = {r.get("client_id"): rid for rid, r in rifs.items() if r.get("client_id")}

    old_stores = {s.get("store_id"): s for s in project.get("stores") or []}
    kept_ids = {b.store_id for b in branches if b.store_id}
    for sid, st in old_stores.items():
        if sid not in kept_ids and is_store_certified(st):
            _fail(f"No se puede eliminar la sucursal «{st.get('name', sid)}»: ya está certificada.")

    new_stores, union = [], {}
    for b in branches:
        name = (b.name or "").strip()
        if not name:
            _fail("Toda sucursal debe tener un nombre.")
        st = dict(old_stores.get(b.store_id) or {})
        if not st:
            st = {"store_id": f"st_{uuid.uuid4().hex[:8]}", "status": "Pendiente", "notes": []}
        rif_id = None
        if b.client_id:
            if b.client_id not in eligible:
                _fail(f"El RIF seleccionado para «{name}» no pertenece al cliente ni a su Grupo Económico.")
            rif_id = by_client.get(b.client_id)
            if not rif_id:
                c = eligible[b.client_id]
                rif_id = f"rif_{uuid.uuid4().hex[:8]}"
                rifs[rif_id] = {"rif_id": rif_id, "client_id": c["client_id"], "rif": c.get("rif") or "",
                                "client_name": c.get("fantasy_name") or c.get("legal_name") or "", "box_count": 0, "status": "Pendiente"}
                by_client[b.client_id] = rif_id
        bps = {}
        for m in b.medios:
            bps.setdefault(m.bank_name.strip(), []).append(m.product_name.strip())
            union.setdefault(m.bank_name.strip(), set()).add(m.product_name.strip())
        from routes.projects import BankProductsOverride
        st.update({
            "name": name,
            "box_count": int(b.box_count or 0),
            "implementation_matrix": build_matrix(
                [BankProductsOverride(bank_name=bn, products=ps) for bn, ps in bps.items()],
                st.get("implementation_matrix", {}),
            ),
        })
        if rif_id:
            r = rifs[rif_id]
            st.update({"rif_id": rif_id, "rif": r.get("rif", ""), "client_name": r.get("client_name", "")})
        new_stores.append(st)

    for r in rifs.values():
        r["box_count"] = sum(s["box_count"] for s in new_stores if s.get("rif_id") == r["rif_id"])
    used_rifs = [r for r in rifs.values() if r["box_count"] > 0 or any(s.get("rif_id") == r["rif_id"] for s in new_stores)]

    update = {
        "stores": new_stores,
        "contract_baseline": baseline,
        "medio_replacements": [r.model_dump() for r in replacements or []],
        "union": union,
    }
    if project.get("rifs") or used_rifs:
        update["rifs"] = used_rifs
    return update
