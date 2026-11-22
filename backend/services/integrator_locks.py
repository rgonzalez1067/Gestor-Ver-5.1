"""Bloqueo de aplicativos certificados/cerrados: Función Especial + motivo obligatorio."""
from datetime import datetime, timezone

from fastapi import HTTPException

from config import db

LOCK_SPECIAL = "integradores:editar_certificados"
CERT_SPECIAL = "integradores:gestionar_certificados"
ACTIVE_SCOPES = ("new", "component", "expansion", "test_environment")

TRACKED = {
    "integrator_type": "Tipo de Integrador", "integration_type": "Tipo de Integración", "app_name": "Nombre del Aplicativo",
    "integration_modality": "Modalidad", "integrator_status": "Estatus", "gestor": "Gestor", "categoria": "Categoría",
    "ticket_number": "Ticket", "integration_phase": "Fase", "coordinador": "Coordinador", "implementador": "Implementador",
    "project_name": "Nombre del Proyecto", "observations": "Observaciones", "comercios_relacionados": "Comercios Relacionados",
    "componente_version": "Componente / Versión", "productos_certificar": "Productos a Certificar",
    "correo_eventual": "Correo Eventual", "principal_contact_name": "Contacto Principal",
    "principal_contact_phone": "Teléfono Contacto Principal", "principal_contact_email": "Email Contacto Principal",
    "interface_negotiation": "Negociación de Interfaz", "contacts": "Contactos Técnicos", "certifications": "Matriz de Productos",
}


def is_active(i):
    return (i or {}).get("project_scope") in ACTIVE_SCOPES and (i or {}).get("integrator_status") != "Cerrado"


def is_locked(i):
    return (i or {}).get("integrator_status") in ("Certificado", "Cerrado") and not is_active(i)


def has_flag(user, flag):
    return (user or {}).get("role") == "admin" or flag in ((user or {}).get("special_permissions") or [])


def _n(v):
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    return v.strip() if isinstance(v, str) else v


def _contacts_key(lst):
    return sorted(((c.get("name") or "").strip(), (c.get("email") or "").strip().lower(), (c.get("phone") or "").strip())
                  for c in (lst or []) if (c.get("name") or "").strip())


def diff_changes(existing, sent, product_names):
    """[(campo, etiqueta, antes, después)] solo para los campos realmente enviados y modificados."""
    out = []
    for k, label in TRACKED.items():
        if k not in sent:
            continue
        before, after = existing.get(k), sent[k]
        if k == "certifications":
            b, a = before or {}, after or {}
            for pid in sorted(set(b) | set(a)):
                vb, va = b.get(pid) or "N/A", a.get(pid) or "N/A"
                if vb != va:
                    out.append((k, f"Matriz · {product_names.get(pid, pid)}", vb, va))
        elif k == "contacts":
            if _contacts_key(before) != _contacts_key(after):
                out.append((k, label, f"{len(_contacts_key(before))} contacto(s)", f"{len(_contacts_key(after))} contacto(s)"))
        elif _n(before) != _n(after):
            out.append((k, label, _n(before) or "—", _n(after) or "—"))
    return out


def enforce_lock(existing, changes, reason, user):
    """Lanza 403/400 si el cambio toca un aplicativo bloqueado sin Función Especial o sin motivo."""
    data_changes = [c for c in changes if c[0] != "certifications"]
    matrix_changes = [c for c in changes if c[0] == "certifications"]
    needs = (is_locked(existing) and data_changes) or (not is_active(existing) and matrix_changes)
    if not needs:
        return False
    if not has_flag(user, LOCK_SPECIAL):
        raise HTTPException(status_code=403, detail=(
            "Aplicativo certificado/cerrado en solo lectura. Requiere la Función Especial "
            "'Modificar Aplicativos Certificados' para editar la Matriz de Productos o sus datos técnicos."))
    if len(reason or "") < 10:
        raise HTTPException(status_code=400, detail="El motivo de la modificación es obligatorio (mínimo 10 caracteres).")
    return True


async def register_locked_change(existing, changes, reason, user):
    now = datetime.now(timezone.utc)
    who = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or user.get("email", "")
    lines = "; ".join(f"{label}: {b} → {a}" for _, label, b, a in changes)
    await db.bitacora.insert_one({
        "entry_id": f"bit_{now.strftime('%H%M%S%f')}", "integrator_id": existing["integrator_id"],
        "description": f"[Modificación de aplicativo certificado] Motivo: {reason}. Cambios: {lines}",
        "contact_id": None, "contact_name": who, "date": now.strftime("%Y-%m-%d"), "commitment": None,
        "commitment_deadline": None, "commitment_completed": False, "created_at": now.isoformat(),
        "kind": "locked_change", "changed_by": user.get("email"),
    })
    if not any(c[0] == "certifications" for c in changes):
        return False
    n = await db.integrator_certificates.count_documents({"integrator_id": existing["integrator_id"]})
    if not n:
        return False
    await db.integrators.update_one({"integrator_id": existing["integrator_id"]}, {"$set": {
        "cert_outdated": True, "cert_outdated_at": now.isoformat(), "cert_outdated_reason": reason, "cert_outdated_by": user.get("email")}})
    await db.integrator_certificates.update_many(
        {"integrator_id": existing["integrator_id"], "$or": [{"status": {"$exists": False}}, {"status": "vigente"}]},
        {"$set": {"status": "desactualizado", "status_updated_at": now.isoformat(), "status_note": reason}})
    return True
