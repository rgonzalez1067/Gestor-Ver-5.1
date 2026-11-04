"""Página "Características particulares del Proyecto" para los PDFs de cotización.

Convierte el HTML del editor enriquecido (TipTap) a flowables de ReportLab.
"""
import html as _html
import io
import re
from html.parser import HTMLParser
from typing import List, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, PageBreak, HRFlowable

FEATURES_TITLE = "CARACTERÍSTICAS PARTICULARES DEL PROYECTO"
MAX_FEATURES_CHARS = 1000
_COLOR_AZUL = colors.HexColor("#1E3A8A")
_ALIGN = {"left": TA_LEFT, "center": TA_CENTER, "right": TA_RIGHT, "justify": TA_JUSTIFY}
_COLOR_RE = re.compile(r"(?<![-\w])color\s*:\s*([^;]+)", re.I)
_BG_RE = re.compile(r"background-color\s*:\s*([^;]+)", re.I)
_ALIGN_RE = re.compile(r"text-align\s*:\s*(left|center|right|justify)", re.I)


def plain_text(value: str) -> str:
    txt = re.sub(r"<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", _html.unescape(txt)).strip()


def has_features(value: Optional[str]) -> bool:
    return bool(plain_text(value or ""))


def _safe_color(raw: str) -> Optional[str]:
    raw = (raw or "").strip()
    m = re.match(r"rgba?\((\d+),\s*(\d+),\s*(\d+)", raw)
    if m:
        return "#%02x%02x%02x" % tuple(int(x) for x in m.groups())
    if raw.lower() in ("inherit", "initial", "transparent", "currentcolor", "unset"):
        return None
    return raw if re.match(r"^#[0-9a-fA-F]{3,8}$|^[a-zA-Z]+$", raw) else None


class _Converter(HTMLParser):
    """HTML (p, h1-3, strong/b, em/i, u, s, span[color], mark, ul/ol/li, br, a) → bloques RL."""

    INLINE = {"strong": "b", "b": "b", "em": "i", "i": "i", "u": "u", "s": "strike", "strike": "strike", "del": "strike"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.blocks = []  # (kind, markup, align, bullet)
        self.buf, self.stack, self.lists = [], [], []
        self.kind, self.align = "p", "left"

    def _flush(self):
        text = "".join(self.buf).strip()
        if text:
            bullet = None
            if self.lists:
                lst = self.lists[-1]
                lst["n"] += 1
                bullet = "•" if lst["type"] == "ul" else f"{lst['n']}."
            self.blocks.append((self.kind, text, self.align, bullet, len(self.lists)))
        self.buf = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        style = a.get("style") or ""
        if tag in ("p", "h1", "h2", "h3", "h4", "li", "div", "blockquote"):
            self._flush()
            self.kind = tag if tag in ("h1", "h2", "h3", "h4") else "p"
            m = _ALIGN_RE.search(style)
            self.align = m.group(1).lower() if m else "left"
        elif tag in ("ul", "ol"):
            self._flush()
            self.lists.append({"type": tag, "n": 0})
        elif tag == "br":
            self.buf.append("<br/>")
        elif tag in self.INLINE:
            self.buf.append(f"<{self.INLINE[tag]}>"); self.stack.append(f"</{self.INLINE[tag]}>")
        elif tag in ("span", "mark", "a"):
            attrs_rl = []
            c = _COLOR_RE.search(style)
            col = _safe_color(c.group(1)) if c else None
            if col:
                attrs_rl.append(f'color="{col}"')
            bg = _BG_RE.search(style)
            bgc = _safe_color(bg.group(1)) if bg else ("#FEF08A" if tag == "mark" else None)
            if bgc:
                attrs_rl.append(f'backColor="{bgc}"')
            if tag == "a" and not col:
                attrs_rl.append('color="#1D4ED8"')
            if attrs_rl:
                self.buf.append(f"<font {' '.join(attrs_rl)}>"); self.stack.append("</font>")
            else:
                self.stack.append("")

    def handle_endtag(self, tag):
        if tag in ("p", "h1", "h2", "h3", "h4", "li", "div", "blockquote"):
            self._flush(); self.kind, self.align = "p", "left"
        elif tag in ("ul", "ol"):
            self._flush()
            if self.lists:
                self.lists.pop()
        elif tag in self.INLINE or tag in ("span", "mark", "a"):
            if self.stack:
                self.buf.append(self.stack.pop())

    def handle_data(self, data):
        self.buf.append(_html.escape(data, quote=False))

    def close(self):
        super().close()
        while self.stack:
            self.buf.append(self.stack.pop())
        self._flush()


def _to_html(value: str) -> str:
    """Texto plano histórico (sin etiquetas) → párrafos."""
    if re.search(r"<\s*(p|ul|ol|h\d|div|br|strong|em|span)\b", value or "", re.I):
        return value
    return "".join(f"<p>{_html.escape(line)}</p>" for line in (value or "").splitlines())


def features_flowables(value: str, page_break_before: bool = False) -> List:
    if not has_features(value):
        return []
    body = ParagraphStyle("FeatBody", fontName="Helvetica", fontSize=10, leading=14, spaceAfter=6, textColor=colors.HexColor("#1F2937"))
    sizes = {"h1": 15, "h2": 13, "h3": 11.5, "h4": 11}
    conv = _Converter()
    conv.feed(_to_html(value))
    conv.close()
    out = [PageBreak()] if page_break_before else []
    out += [
        Paragraph(FEATURES_TITLE, ParagraphStyle("FeatTitle", fontName="Helvetica-Bold", fontSize=14, textColor=_COLOR_AZUL, spaceAfter=6)),
        HRFlowable(width="100%", thickness=1.2, color=_COLOR_AZUL, spaceAfter=12),
    ]
    for kind, markup, align, bullet, depth in conv.blocks:
        st = ParagraphStyle(f"F_{kind}_{align}_{depth}", parent=body, alignment=_ALIGN.get(align, TA_LEFT))
        if kind in sizes:
            st.fontName, st.fontSize, st.leading, st.textColor = "Helvetica-Bold", sizes[kind], sizes[kind] + 4, _COLOR_AZUL
        if bullet:
            st.leftIndent = 14 * depth + 4
            st.bulletIndent = 14 * (depth - 1) + 2
        try:
            out.append(Paragraph(markup, st, bulletText=bullet))
        except Exception:  # noqa: BLE001 — markup inesperado: degradar a texto plano
            out.append(Paragraph(_html.escape(plain_text(markup)), st, bulletText=bullet))
    return out


def build_features_pdf(value: str, logo_path: Optional[str] = None) -> Optional[bytes]:
    """PDF independiente (1 página) para insertar en flujos que fusionan PDFs."""
    if not has_features(value):
        return None
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=2.6 * cm, bottomMargin=2 * cm)

    def _header(c, _d):
        if logo_path:
            try:
                c.drawImage(logo_path, 2 * cm, letter[1] - 2.1 * cm, width=4 * cm, height=1.3 * cm,
                            preserveAspectRatio=True, anchor="w", mask="auto")
            except Exception:  # noqa: BLE001
                pass

    doc.build([Spacer(1, 4)] + features_flowables(value), onFirstPage=_header, onLaterPages=_header)
    return buf.getvalue()


def insert_pdf_before_tail(pdf_bytes: bytes, insert_bytes: Optional[bytes], tail_pages: int = 0) -> bytes:
    """Inserta `insert_bytes` antes de las últimas `tail_pages` páginas (0 = al final)."""
    if not insert_bytes:
        return pdf_bytes
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        from PyPDF2 import PdfReader, PdfWriter
    base = list(PdfReader(io.BytesIO(pdf_bytes)).pages)
    ins = list(PdfReader(io.BytesIO(insert_bytes)).pages)
    cut = max(0, len(base) - tail_pages)
    w = PdfWriter()
    for p in base[:cut] + ins + base[cut:]:
        w.add_page(p)
    out = io.BytesIO()
    w.write(out)
    return out.getvalue()
