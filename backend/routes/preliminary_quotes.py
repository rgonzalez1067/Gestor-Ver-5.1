"""Cotizaciones preliminares (Cliente Sin Rif, prefijo PRE): asignación de cliente
definitivo (→ COT) y envío simple por correo con PDF marcado PRELIMINAR."""
import io
import logging
import re
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel, EmailStr

from config import db, get_current_user, SIN_RIF_CLIENT_ID, generate_quote_number

router = APIRouter()

PRE_BLOCK_MSG = ("Acción no permitida: La cotización preliminar debe ser asignada a un cliente formal "
                 "antes de continuar el flujo operativo.")
# Acciones de flujo bloqueadas para PRE (se valida en middleware).
BLOCKED_PRE_ACTIONS = re.compile(
    r"^/api/quotes/([^/]+)/(status|approve|configure|repair-complete|send-to-client|send-to-implementation|"
    r"invoice|collect|deliver|repair-deliver|duplicate|pdf|equipos-infra)$"
)


def is_preliminary(quote: dict) -> bool:
    return (quote.get("quote_number") or "").startswith("PRE-") or quote.get("client_id") == SIN_RIF_CLIENT_ID


class AssignClientRequest(BaseModel):
    client_id: str


class SendPreliminaryRequest(BaseModel):
    email: EmailStr


async def _load_pre(quote_id: str) -> dict:
    quote = await db.quotes.find_one({"quote_id": quote_id}, {"_id": 0})
    if not quote:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    if not is_preliminary(quote):
        raise HTTPException(status_code=400, detail="La cotización no es preliminar.")
    return quote


@router.post("/quotes/{quote_id}/assign-client")
async def assign_client(quote_id: str, data: AssignClientRequest, authorization: Optional[str] = Header(None)):
    current_user = await get_current_user(authorization)
    quote = await _load_pre(quote_id)
    if data.client_id == SIN_RIF_CLIENT_ID:
        raise HTTPException(status_code=400, detail="Seleccione un cliente con RIF real.")
    client = await db.clients.find_one({"client_id": data.client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    old_number = quote["quote_number"]
    sede = (old_number.rsplit("-", 1)[-1] if old_number.startswith("PRE-") else quote.get("client_segment")) or "PYME"
    new_number = await generate_quote_number(sede, data.client_id)
    now = datetime.now(timezone.utc).isoformat()
    name = client.get("fantasy_name") or client.get("legal_name") or ""
    res = await db.quotes.update_one(
        {"quote_id": quote_id, "quote_number": old_number},
        {"$set": {"client_id": data.client_id, "client_name": name, "quote_number": new_number,
                  "preliminary_number": old_number, "assigned_client_at": now,
                  "assigned_client_by": current_user.get("email")}},
    )
    if not res.modified_count:
        raise HTTPException(status_code=409, detail="La cotización fue modificada por otro usuario. Recargue e intente de nuevo.")
    await db.audit_exceptions.insert_one({
        "quote_id": quote_id, "quote_number": new_number, "action": "preliminary_assigned",
        "description": f"Cotización preliminar {old_number} asignada a {name} ({client.get('rif', '')}) → {new_number}",
        "user_id": current_user.get("user_id"), "user_email": current_user.get("email"),
        "user_name": current_user.get("name") or current_user.get("email"), "created_at": now,
    })

    # Regenerar el PDF con el número y cliente definitivos.
    try:
        commercial = {"VPOS", "MPOS", "GATEWAY", "LINK_PAGO", "FAST_TRACK", "VPOS_MULTIRIF"}
        if quote.get("quote_type") not in commercial:
            from routes.quotes import regenerate_equipment_pdf
            await regenerate_equipment_pdf(quote_id, {}, authorization)
        else:
            from routes.quotes import regenerate_quote_pdf
            await regenerate_quote_pdf(quote_id, {}, authorization)
    except Exception as e:
        logging.warning(f"[assign-client] no se pudo regenerar el PDF de {new_number}: {e}")
    return {"quote_number": new_number, "preliminary_number": old_number, "client_name": name}


def _watermark(pdf_bytes: bytes) -> bytes:
    from PyPDF2 import PdfReader, PdfWriter
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import Color
    reader, writer = PdfReader(io.BytesIO(pdf_bytes)), PdfWriter()
    for page in reader.pages:
        w, h = float(page.mediabox.width), float(page.mediabox.height)
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=(w, h))
        c.setFillColor(Color(0.86, 0.15, 0.15, alpha=0.18))
        c.setFont("Helvetica-Bold", 96)
        c.translate(w / 2, h / 2)
        c.rotate(40)
        c.drawCentredString(0, -30, "PRELIMINAR")
        c.save()
        page.merge_page(PdfReader(io.BytesIO(buf.getvalue())).pages[0])
        writer.add_page(page)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


@router.post("/quotes/{quote_id}/send-preliminary")
async def send_preliminary(quote_id: str, data: SendPreliminaryRequest, authorization: Optional[str] = Header(None)):
    current_user = await get_current_user(authorization)
    quote = await _load_pre(quote_id)
    url = quote.get("quote_pdf_url") or ""
    from services.pdf_storage import load_attachment_bytes
    pdf_bytes = load_attachment_bytes(url) if url else None
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="La cotización no tiene PDF generado. Modifíquela y guárdela para generarlo.")
    pdf = _watermark(pdf_bytes)

    from services.email_service import send_email
    number = quote["quote_number"]
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:600px;margin:0 auto;">
      <div style="background:#003366;padding:18px;border-radius:8px 8px 0 0;"><h2 style="color:#fff;margin:0;">Mega Soft Computación</h2></div>
      <div style="padding:24px;border:1px solid #e2e8f0;border-top:none;border-radius:0 0 8px 8px;color:#334155;">
        <p>Estimado(a),</p>
        <p>Adjuntamos la propuesta comercial <b>preliminar</b> {number}. Los montos y condiciones son referenciales
        y se formalizarán al registrar los datos fiscales del cliente.</p>
        <p>Saludos,<br><b>{current_user.get('name') or ''}</b><br>{current_user.get('email')}</p>
      </div>
    </div>"""
    result = await send_email(
        to=[data.email], subject=f"Cotización preliminar {number} — Mega Soft", html=html,
        action="preliminary_quote", quote_id=quote_id, quote_number=number,
        attachments=[{"filename": f"{number}-PRELIMINAR.pdf", "content": pdf, "content_type": "application/pdf"}],
        reply_to=current_user.get("email"),
    )
    if isinstance(result, dict) and result.get("status") == "error":
        raise HTTPException(status_code=502, detail=f"No se pudo enviar el correo: {result.get('error', '')}")
    return {"message": f"Cotización preliminar enviada exitosamente a {data.email}"}
