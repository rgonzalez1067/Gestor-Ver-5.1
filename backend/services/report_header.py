"""Encabezado repetido en cada página (logo Mega Soft + título) para reportes PDF.

- `html_with_page_header(html, title)`: reportes WeasyPrint (elemento running en @top-left).
- `draw_page_header(canvas, doc, title)`: reportes ReportLab (usar en onFirstPage/onLaterPages).
"""
import base64
import re
from functools import lru_cache
from pathlib import Path

from reportlab.lib import colors

LOGO_PATH = Path(__file__).resolve().parent.parent / "uploads" / "logo.png"
BRAND = "Gestor - CRM"
COLOR_AZUL = colors.HexColor("#00447C")


def logo_path_or_none():
    return str(LOGO_PATH) if LOGO_PATH.exists() else None


@lru_cache(maxsize=1)
def _logo_data_uri():
    if not LOGO_PATH.exists():
        return ""
    return "data:image/png;base64," + base64.b64encode(LOGO_PATH.read_bytes()).decode()


def html_with_page_header(html: str, title: str) -> str:
    logo = _logo_data_uri()
    logo_tag = f'<img src="{logo}" style="height:30px;" />' if logo else ""
    css = """<style>
  @page { margin-top: 28mm; @top-left { content: element(pageHeader); width: 100%; vertical-align: bottom; padding-bottom: 3mm; } }
  .page-running-header { position: running(pageHeader); display: flex; align-items: center; gap: 10px;
    border-bottom: 1.5px solid #00447C; padding-bottom: 4px; font-family: Helvetica, Arial, sans-serif; }
  .page-running-header .prh-title { flex: 1; font-size: 11px; font-weight: 700; color: #00447C; }
  .page-running-header .prh-brand { font-size: 8.5px; color: #64748b; }
</style>"""
    header = (f'<div class="page-running-header">{logo_tag}<span class="prh-title">{title}</span>'
              f'<span class="prh-brand">{BRAND}</span></div>')
    html = html.replace("</head>", css + "</head>", 1) if "</head>" in html else css + html
    m = re.search(r"<body[^>]*>", html)
    return html[:m.end()] + header + html[m.end():] if m else header + html


def draw_page_header(canvas, doc, title: str):
    """Dibuja logo (izq.), título y marca en la banda superior; requiere topMargin >= ~2.2 cm."""
    page_w, page_h = doc.pagesize
    canvas.saveState()
    top = page_h - 0.55 * 28.35
    logo = logo_path_or_none()
    x_title = doc.leftMargin
    if logo:
        try:
            canvas.drawImage(logo, doc.leftMargin, top - 30, width=80, height=30, preserveAspectRatio=True, mask="auto")
            x_title = doc.leftMargin + 90
        except Exception:
            pass
    canvas.setFont("Helvetica-Bold", 11)
    canvas.setFillColor(COLOR_AZUL)
    canvas.drawString(x_title, top - 19, title)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#64748b"))
    canvas.drawRightString(page_w - doc.rightMargin, top - 19, BRAND)
    canvas.setStrokeColor(COLOR_AZUL)
    canvas.setLineWidth(1)
    canvas.line(doc.leftMargin, top - 36, page_w - doc.rightMargin, top - 36)
    canvas.restoreState()
