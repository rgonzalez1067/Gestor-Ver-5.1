"""Carga masiva de sucursales de un RIF desde Excel (plantilla + vista previa + confirmación)."""
import io
import re
import uuid
from typing import Optional

from fastapi import APIRouter, HTTPException, Header, UploadFile, File
from fastapi.responses import StreamingResponse

from config import db, require_permission
from routes.clients import create_branch, update_branch_data

router = APIRouter()

ROLES = ["Administrativo", "Financiero", "Técnico", "Cuentas por Pagar", "Operativo", "Propietario", "Director", "Integrador"]
HEADERS = ["Nombre Sucursal *", "Dirección Física *", "Cajas *", "Contacto Nombre", "Contacto Cargo", "Contacto Teléfono", "Contacto Correo"]
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


async def _principal(client_id: str) -> dict:
    p = await db.clients.find_one({"client_id": client_id}, {"_id": 0, "client_id": 1, "rif": 1, "legal_name": 1, "is_branch": 1})
    if not p or p.get("is_branch"):
        raise HTTPException(status_code=404, detail="RIF principal no encontrado")
    return p


@router.get("/clients/{client_id}/branches/import-template")
async def branches_template(client_id: str, authorization: Optional[str] = Header(None)):
    await require_permission(authorization, "clientes", "view")
    p = await _principal(client_id)
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment
    from openpyxl.worksheet.datavalidation import DataValidation
    wb = Workbook()
    ws = wb.active
    ws.title = "Sucursales"
    ws.append(HEADERS)
    for i, c in enumerate(ws[1]):
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="D97706" if i < 3 else "64748B")
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.append(["Sucursal Altamira", "Av. Luis Roche, Edif. Altamira, PB, Caracas", 3, "Pedro Pérez", "Administrativo", "0414-1234567", "pedro.perez@empresa.com"])
    ws.append(["Sucursal Chacao", "C.C. Sambil, Nivel Acuario, Local 12", 2, "", "", "", ""])
    for col, w in zip("ABCDEFG", (30, 48, 9, 24, 18, 18, 30)):
        ws.column_dimensions[col].width = w
    ws.row_dimensions[1].height = 30
    ws.freeze_panes = "A2"
    dv = DataValidation(type="list", formula1='"' + ",".join(ROLES) + '"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add("E2:E1000")
    dvn = DataValidation(type="whole", operator="greaterThanOrEqual", formula1="1", allow_blank=False)
    ws.add_data_validation(dvn)
    dvn.add("C2:C1000")
    ins = wb.create_sheet("Instrucciones")
    for line in [
        f"Carga masiva de sucursales para: {p.get('rif')} — {p.get('legal_name')}",
        "",
        "1. Complete una fila por sucursal en la hoja 'Sucursales'. Borre las 2 filas de ejemplo.",
        "2. Columnas obligatorias (naranja): Nombre Sucursal (máx. 150, distinto de 'Principal'), Dirección Física y Cajas (entero ≥ 1).",
        "3. Contacto (gris) es opcional. Si lo indica, requiere Nombre y un Correo válido o Teléfono.",
        "   Sin contacto, la sucursal hereda los contactos del RIF.",
        "4. Si el nombre de la sucursal ya existe en este RIF, se ACTUALIZAN su dirección, cajas y contacto.",
        f"5. Cargos válidos: {', '.join(ROLES)}.",
        "6. Suba el archivo desde la ficha del RIF > Sucursales > Importar Excel. Verá una vista previa antes de confirmar.",
    ]:
        ins.append([line])
    ins["A1"].font = Font(bold=True, size=12, color="92400E")
    ins.column_dimensions["A"].width = 120
    buf = io.BytesIO()
    wb.save(buf)
    safe = re.sub(r"[^A-Za-z0-9]+", "_", p.get("rif") or "RIF")
    return StreamingResponse(io.BytesIO(buf.getvalue()), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             headers={"Content-Disposition": f'attachment; filename="Plantilla_Sucursales_{safe}.xlsx"'})


def _cell(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    return str(v).strip()


async def _analyze(client_id: str, content: bytes) -> dict:
    from openpyxl import load_workbook
    try:
        wb = load_workbook(io.BytesIO(content), data_only=True)
    except Exception:
        raise HTTPException(status_code=400, detail="Archivo inválido: suba la plantilla .xlsx")
    ws = wb["Sucursales"] if "Sucursales" in wb.sheetnames else wb.active
    existing = {(b.get("sucursal") or "").strip().lower(): b for b in await db.clients.find(
        {"parent_client_id": client_id, "is_branch": True}, {"_id": 0, "client_id": 1, "sucursal": 1, "contacts": 1}).to_list(None)}
    rows, seen = [], set()
    for idx, raw in enumerate(ws.iter_rows(min_row=2, max_col=7, values_only=True), start=2):
        vals = [_cell(v) for v in raw] + [""] * (7 - len(raw))
        if not any(vals):
            continue
        name, addr, cajas_s, c_name, c_role, c_phone, c_email = vals[:7]
        errors = []
        if not name:
            errors.append("Nombre de sucursal vacío")
        elif name.lower() == "principal":
            errors.append("El nombre no puede ser 'Principal'")
        elif len(name) > 150:
            errors.append("Nombre supera 150 caracteres")
        elif name.lower() in seen:
            errors.append("Sucursal repetida en el archivo")
        if not addr:
            errors.append("Dirección física vacía")
        try:
            cajas = int(float(cajas_s))
            if cajas < 1:
                raise ValueError
        except ValueError:
            cajas = None
            errors.append("Cajas debe ser un entero ≥ 1")
        contact = None
        if any((c_name, c_role, c_phone, c_email)):
            if not c_name:
                errors.append("Contacto sin nombre")
            if c_email and not EMAIL_RE.match(c_email):
                errors.append("Correo de contacto inválido")
            if not c_email and not c_phone:
                errors.append("Contacto requiere correo o teléfono")
            if c_role and c_role not in ROLES:
                errors.append(f"Cargo '{c_role}' no válido")
            contact = {"full_name": c_name, "role": c_role or "Administrativo", "phone": c_phone, "email": c_email.lower()}
        seen.add(name.lower())
        match = existing.get(name.lower())
        rows.append({"row": idx, "sucursal": name, "branch_address": addr, "cantidad_cajas": cajas, "contact": contact,
                     "action": "update" if match else "create", "client_id": match["client_id"] if match else None, "errors": errors})
    if not rows:
        raise HTTPException(status_code=400, detail="El archivo no tiene filas de sucursales")
    ok = [r for r in rows if not r["errors"]]
    return {"rows": rows, "summary": {"total": len(rows), "valid": len(ok), "errors": len(rows) - len(ok),
                                      "create": sum(r["action"] == "create" for r in ok), "update": sum(r["action"] == "update" for r in ok)},
            "_existing": existing}


@router.post("/clients/{client_id}/branches/import")
async def branches_import(client_id: str, confirm: bool = False, file: UploadFile = File(...), authorization: Optional[str] = Header(None)):
    await require_permission(authorization, "clientes", "edit")
    await _principal(client_id)
    res = await _analyze(client_id, await file.read())
    existing = res.pop("_existing")
    if not confirm:
        return res
    created = updated = 0
    failed = []
    for r in res["rows"]:
        if r["errors"]:
            continue
        try:
            if r["action"] == "create":
                payload = {"sucursal": r["sucursal"], "branch_address": r["branch_address"], "cantidad_cajas": r["cantidad_cajas"],
                           "contacts": [{**r["contact"], "contact_id": f"cnt_{uuid.uuid4().hex[:8]}", "purposes": []}] if r["contact"] else []}
                await create_branch(client_id, payload, authorization)
                created += 1
            else:
                contacts = list(existing[r["sucursal"].lower()].get("contacts") or [])
                if r["contact"]:
                    key = r["contact"]["email"] or r["contact"]["full_name"].lower()
                    i = next((j for j, c in enumerate(contacts) if key in ((c.get("email") or "").lower(), (c.get("full_name") or "").lower())), None)
                    if i is None:
                        contacts.append({**r["contact"], "purposes": []})
                    else:
                        contacts[i] = {**contacts[i], **r["contact"]}
                await update_branch_data(r["client_id"], {"sucursal": r["sucursal"], "branch_address": r["branch_address"],
                                                          "cantidad_cajas": r["cantidad_cajas"], "contacts": contacts}, authorization)
                updated += 1
        except HTTPException as e:
            failed.append({"row": r["row"], "sucursal": r["sucursal"], "error": e.detail})
    return {"created": created, "updated": updated, "failed": failed, "skipped": res["summary"]["errors"]}
