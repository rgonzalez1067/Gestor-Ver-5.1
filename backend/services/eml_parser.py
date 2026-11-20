"""Parser de correos .eml (descargados de Gmail/Outlook) para visualizarlos dentro del sistema."""
import base64
import email
from email import policy
from typing import Optional


def load_eml(data: bytes):
    msg = email.message_from_bytes(data, policy=policy.default)
    if not (msg.get("From") or msg.get("Subject") or msg.get("Date")):
        return None
    return msg


def _parts(msg):
    """Separa el cuerpo (html/text), imágenes inline (cid) y adjuntos descargables."""
    html, text, inline, attachments = None, None, {}, []
    for part in msg.walk():
        if part.is_multipart():
            continue
        ctype = part.get_content_type()
        disp = part.get_content_disposition()
        filename = part.get_filename()
        cid = (part.get("Content-ID") or "").strip("<> ")
        if disp != "attachment" and not filename and ctype == "text/html" and html is None:
            html = part.get_content()
        elif disp != "attachment" and not filename and ctype == "text/plain" and text is None:
            text = part.get_content()
        elif cid and disp != "attachment" and ctype.startswith("image/"):
            inline[cid] = (ctype, part.get_payload(decode=True) or b"")
        else:
            attachments.append({"part": part, "filename": filename or f"adjunto_{len(attachments) + 1}",
                                "content_type": ctype})
    return html, text, inline, attachments


def eml_summary(data: bytes) -> Optional[dict]:
    msg = load_eml(data)
    if msg is None:
        return None
    html, text, inline, attachments = _parts(msg)
    if html:
        for cid, (ctype, payload) in inline.items():
            html = html.replace(f"cid:{cid}", f"data:{ctype};base64,{base64.b64encode(payload).decode()}")
    return {
        "from": str(msg.get("From") or ""), "to": str(msg.get("To") or ""), "cc": str(msg.get("Cc") or ""),
        "subject": str(msg.get("Subject") or ""), "date": str(msg.get("Date") or ""),
        "html": html, "text": text,
        "attachments": [{"index": i, "filename": a["filename"], "content_type": a["content_type"],
                         "size": len(a["part"].get_payload(decode=True) or b"")} for i, a in enumerate(attachments)],
    }


def eml_attachment(data: bytes, index: int):
    msg = load_eml(data)
    if msg is None:
        return None
    _, _, _, attachments = _parts(msg)
    if index < 0 or index >= len(attachments):
        return None
    a = attachments[index]
    return a["filename"], a["content_type"], a["part"].get_payload(decode=True) or b""
