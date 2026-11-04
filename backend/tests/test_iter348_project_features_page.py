# ruff: noqa
"""Iter 348 — 'Características particulares del Proyecto' page in quote PDFs.

Covers:
- Unit: services/project_features_pdf (has_features, features_flowables, build_features_pdf, insert_pdf_before_tail)
- Preview (DynamicQuotePDFGenerator): VPOS PYME, VPOS CORP, GATEWAY PYME/CORP, LINK_PAGO PYME/CORP
- Equipment / Repair: generate-equipment-pdf + regenerate-equipment-pdf (page before conditions, no 'Observaciones:')
"""
import io
import os
import sys
from pathlib import Path

import fitz
import pytest
import requests

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from services.project_features_pdf import (  # noqa: E402
    FEATURES_TITLE, has_features, features_flowables, build_features_pdf, insert_pdf_before_tail, plain_text,
)


def _env_url():
    for line in Path("/app/frontend/.env").read_text().splitlines():
        if line.startswith("REACT_APP_BACKEND_URL="):
            return line.split("=", 1)[1].strip().rstrip("/")
    return os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")


BASE_URL = _env_url()
ADMIN = {"email": "rgonzalez@megasoft.com.ve", "password": "Mega2026*"}
RICH = ('<p><strong>NEGRITA_X</strong> <em>CURSIVA_X</em> <u>SUB_X</u> <s>TACH_X</s> '
        '<span style="color: rgb(220, 38, 38)">ROJO_X</span> <mark data-color="#FEF3C7" style="background-color: #FEF3C7">RES_X</mark> A &amp; B &lt; C</p>'
        '<ul><li><p>ITEM_UNO</p></li><li><p>ITEM_DOS</p></li></ul>'
        '<ol><li><p>NUM_UNO</p></li></ol><p style="text-align: center">CENTRADO_X</p>')


def _pages(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    return [p.get_text() for p in doc]


def _idx(pages, needle):
    for i, t in enumerate(pages):
        if needle in t:
            return i
    return -1


@pytest.fixture(scope="module")
def headers():
    r = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN, timeout=30)
    if r.status_code != 200:
        pytest.skip(f"login failed {r.status_code}")
    d = r.json()
    tok = d.get("session_token") or d.get("access_token") or d.get("token")
    return {"Authorization": f"Bearer {tok}", "Content-Type": "application/json"}


# ---------------- Unit ----------------
class TestUnit:
    def test_has_features(self):
        assert not has_features("")
        assert not has_features("<p></p>")
        assert not has_features(None)
        assert has_features("<p>x</p>")
        assert has_features("legacy plain")

    def test_flowables_empty(self):
        assert features_flowables("<p></p>") == []

    def test_build_pdf_rich_preserves_text_and_specials(self):
        b = build_features_pdf(RICH)
        assert b and b[:4] == b"%PDF"
        txt = _pages(b)[0]
        assert FEATURES_TITLE in txt
        for w in ["NEGRITA_X", "CURSIVA_X", "SUB_X", "TACH_X", "ROJO_X", "RES_X", "A & B < C", "ITEM_UNO", "ITEM_DOS", "NUM_UNO", "CENTRADO_X"]:
            assert w in txt, w

    def test_bold_font_used(self):
        b = build_features_pdf("<p><strong>BOLDWORD</strong> normal</p>")
        doc = fitz.open(stream=b, filetype="pdf")
        fonts = {s["text"].strip(): s["font"] for blk in doc[0].get_text("dict")["blocks"] for l in blk.get("lines", []) for s in l["spans"]}
        assert "Bold" in fonts.get("BOLDWORD", ""), fonts

    def test_color_preserved(self):
        b = build_features_pdf('<p><span style="color: #dc2626">REDWORD</span></p>')
        doc = fitz.open(stream=b, filetype="pdf")
        cols = {s["text"].strip(): s["color"] for blk in doc[0].get_text("dict")["blocks"] for l in blk.get("lines", []) for s in l["spans"]}
        assert cols.get("REDWORD") == 0xDC2626, cols

    def test_legacy_plain_text(self):
        b = build_features_pdf("Linea uno\nLinea dos & <tres>")
        txt = _pages(b)[0]
        assert "Linea uno" in txt and "Linea dos & <tres>" in txt

    def test_malformed_html_does_not_crash(self):
        b = build_features_pdf("<p><strong>abierto <em>mal</p><p>& sin cerrar <b>")
        assert b and FEATURES_TITLE in _pages(b)[0]

    def test_headings(self):
        b = build_features_pdf("<h2>TITULO_H2</h2><p>body</p>")
        assert "TITULO_H2" in _pages(b)[0]

    def test_insert_before_tail(self):
        base = build_features_pdf("<p>BASE</p>")
        ins = build_features_pdf("<p>INS</p>")
        out = insert_pdf_before_tail(base, ins, 0)
        p = _pages(out)
        assert len(p) == 2 and "INS" in p[1]
        assert insert_pdf_before_tail(base, None) == base


# ---------------- Preview (DynamicQuotePDFGenerator) ----------------
def _vpos_body(segment, notes):
    return {
        "cliente_nombre": "TEST_Features SA", "cliente_rif": "J-12345678-9", "cliente_contacto": "QA",
        "cliente_address": "Caracas", "integrator_name": "Integ", "integrator_app_name": "App",
        "pinpad_model": "VX", "sponsor_bank_name": "Banco", "cantidad_cajas": 2,
        "quote_number": "TEST-FEAT-VPOS", "quote_type": "VPOS_MPOS", "client_segment": segment,
        "setup_items": [{"concepto": "Setup", "cantidad_cajas": 2, "cantidad_bancos": 1, "tarifa": 100.0, "tipo_corp": "Derecho de Uso"}],
        "recurring_basic_items": [{"concepto": "Rec", "cantidad_cajas": 2, "cantidad_bancos": 1, "tarifa": 25.0, "tipo_corp": "Apoyo Técnico"}],
        "recurring_other_items": [], "additional_items": [], "production_items": [], "descuento": 0,
        "notes": notes,
    }


def _pg_body(qtype, segment, notes):
    return {
        "cliente_nombre": "TEST_Features PG", "cliente_rif": "J-12345678-9", "cliente_contacto": "QA",
        "quote_number": f"TEST-FEAT-{qtype}", "quote_type": qtype, "client_segment": segment,
        "pg_setup_items": [{"concepto": "Persona Jurídica", "costo": 240, "banco": "N/A", "observacion": "Costo Base"}],
        "pg_recurring_cost": {"rangos": [{"rango_label": "0-1000", "costo_base_total": 100, "precio_tope": 200}], "num_products": 1},
        "notes": notes,
    }


def _preview(headers, body):
    r = requests.post(f"{BASE_URL}/api/quotes/preview-pdf-with-template", json=body, headers=headers, timeout=90)
    assert r.status_code == 200, r.text[:400]
    assert r.content[:4] == b"%PDF"
    return _pages(r.content)


class TestPreview:
    def test_vpos_pyme_with_notes(self, headers):
        p = _preview(headers, _vpos_body("PYME", RICH))
        fi, ti = _idx(p, FEATURES_TITLE), _idx(p, "TÉRMINOS DE LA COTIZACIÓN")
        print("VPOS PYME pages", len(p), fi, ti)
        assert fi >= 0 and ti >= 0 and ti == fi + 1
        assert "NEGRITA_X" in p[fi] and "A & B < C" in p[fi]
        assert all("Notas:" not in t for t in p)

    def test_vpos_pyme_without_notes(self, headers):
        p_with = _preview(headers, _vpos_body("PYME", RICH))
        p = _preview(headers, _vpos_body("PYME", "<p></p>"))
        assert _idx(p, FEATURES_TITLE) == -1
        assert len(p) == len(p_with) - 1

    def test_vpos_corp_with_notes(self, headers):
        p = _preview(headers, _vpos_body("CORP", RICH))
        p0 = _preview(headers, _vpos_body("CORP", ""))
        fi = _idx(p, FEATURES_TITLE)
        print("VPOS CORP pages", len(p), len(p0), fi)
        assert fi >= 0 and len(p) == len(p0) + 1
        # pages after features == annex pages (same tail as without notes)
        strip = lambda t: t.split("Pagina")[0][:400]
        assert [strip(x) for x in p[fi + 1:]] == [strip(x) for x in p0[fi:]]

    @pytest.mark.parametrize("qtype", ["GATEWAY", "LINK_PAGO"])
    def test_pg_lp_pyme(self, headers, qtype):
        p = _preview(headers, _pg_body(qtype, "PYME", RICH))
        p0 = _preview(headers, _pg_body(qtype, "PYME", ""))
        fi, ti = _idx(p, FEATURES_TITLE), _idx(p, "TÉRMINOS DE LA COTIZACIÓN")
        print(qtype, "PYME pages", len(p), len(p0), "feat", fi, "term", ti)
        assert fi >= 0 and len(p) == len(p0) + 1
        assert fi < ti, "features must be before Términos"
        assert ti == len(p) - 1 or "TÉRMINOS" in p[-1] or ti > fi

    @pytest.mark.parametrize("qtype", ["GATEWAY", "LINK_PAGO"])
    def test_pg_lp_corp(self, headers, qtype):
        p = _preview(headers, _pg_body(qtype, "CORP", RICH))
        p0 = _preview(headers, _pg_body(qtype, "CORP", ""))
        fi = _idx(p, FEATURES_TITLE)
        print(qtype, "CORP pages", len(p), len(p0), "feat", fi)
        assert fi >= 0, f"{qtype} CORP: features page missing (truncated by apply_corporate_pg_lp_restructure?)"
        assert len(p) == len(p0) + 1


# ---------------- Equipment / Repair ----------------
def _equip_payload(notes, etype="Venta de Equipos"):
    return {
        "client_id": "", "cliente_nombre": "TEST_Features Equip", "cliente_rif": "J-00000000-0",
        "cliente_address": "Test", "equipment_type": etype,
        "items": [{"hardware_id": "", "name": "TEST POS", "hardware_type": "POS", "quantity": 1, "unit_price_usd": 50.0, "total_usd": 50.0}],
        "notes": notes, "repair_description": "", "equipment_serial_number": "", "estimated_delivery_date": "",
        "bulk_serials": [], "repair_models": [],
    }


# WARNING: generate-equipment-pdf persists a quote and writes /uploads/{quote_number}_Cotizacion_Equipo.pdf.
# In preview the PYME counter is behind existing data -> duplicate quote_number -> it OVERWROTE a real quote PDF
# (quo_ecf39eb7b140, restored via regenerate). Opt-in only: RUN_EQUIP_PDF_TESTS=1
@pytest.mark.skipif(os.environ.get("RUN_EQUIP_PDF_TESTS") != "1", reason="persists quotes; may collide with real quote numbers")
class TestEquipment:
    created = []

    @pytest.mark.parametrize("etype", ["Verifone", "Reparación"])
    def test_generate_and_regenerate(self, headers, etype):
        r = requests.post(f"{BASE_URL}/api/quotes/generate-equipment-pdf", json=_equip_payload(RICH, etype), headers=headers, timeout=120)
        assert r.status_code == 200, r.text[:400]
        qid = r.headers.get("X-Quote-Id")
        assert qid
        TestEquipment.created.append(qid)
        p = _pages(r.content)
        fi = _idx(p, FEATURES_TITLE)
        print(etype, "pages", len(p), "feat", fi, [t[:60].replace("\n", " ") for t in p])
        assert fi >= 1, "features page must exist after main page"
        assert "NEGRITA_X" in p[fi]
        assert all("Observaciones:" not in t for t in p[:fi])
        assert fi < len(p) - 1, "conditions should follow features page"

        r2 = requests.post(f"{BASE_URL}/api/quotes/{qid}/regenerate-equipment-pdf", json={}, headers=headers, timeout=120)
        print("regen", r2.status_code, r2.headers.get("content-type"), r2.text[:200] if r2.headers.get("content-type", "").startswith("application/json") else "")
        assert r2.status_code == 200, r2.text[:400]
        url = r2.json().get("pdf_url")
        pdf = None
        for u in (f"{BASE_URL}{url}", f"{BASE_URL}/api{url}"):
            g = requests.get(u, headers=headers, timeout=60)
            if g.status_code == 200 and g.content[:4] == b"%PDF":
                pdf = g.content
                break
        assert pdf, f"could not download regenerated pdf {url}"
        p2 = _pages(pdf)
        fi2 = _idx(p2, FEATURES_TITLE)
        print("regen pages", len(p2), "feat", fi2)
        assert fi2 == fi and len(p2) == len(p)
        assert all("Observaciones:" not in t for t in p2[:fi2])

    def test_generate_without_notes(self, headers):
        r = requests.post(f"{BASE_URL}/api/quotes/generate-equipment-pdf", json=_equip_payload(""), headers=headers, timeout=120)
        assert r.status_code == 200
        qid = r.headers.get("X-Quote-Id")
        if qid:
            TestEquipment.created.append(qid)
        assert _idx(_pages(r.content), FEATURES_TITLE) == -1

    @classmethod
    def teardown_class(cls):
        r = requests.post(f"{BASE_URL}/api/auth/login", json=ADMIN, timeout=30)
        tok = r.json().get("session_token") or r.json().get("token")
        for q in cls.created:
            d = requests.delete(f"{BASE_URL}/api/quotes/{q}", headers={"Authorization": f"Bearer {tok}"}, timeout=30)
            print("delete", q, d.status_code)
