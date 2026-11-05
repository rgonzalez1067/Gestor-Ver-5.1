import sys
sys.path.insert(0, '/app/backend')
from PyPDF2 import PdfReader
from services.pdf_generator import TemplateQuotePDFRequest, DynamicQuotePDFGenerator

base = dict(cliente_nombre="Cliente Demo", cliente_rif="J123", integrator_name="Integ", integrator_app_name="App",
            pg_setup_items=[{"concepto": "Persona Jurídica", "costo": 240, "banco": "N/A"}, {"concepto": "C2P (PG)", "costo": 36, "banco": "Banco X"}])

def run(label, **kw):
    req = TemplateQuotePDFRequest(**{**base, **kw})
    buf = DynamicQuotePDFGenerator(req, None).generate()
    buf.seek(0)
    pages = [(p.extract_text() or '') for p in PdfReader(buf).pages]
    txt = "\n".join(pages)
    print(f"{label}: pages={len(pages)} PG_setup={'INVERSIÓN EN SETUP' in txt} tok={'Tarifa del Tokenizador' in txt} link={'Tarifas de Link de Pago' in txt} PersonaJur240={'$240.00' in txt}")

run("PG solo", quote_type="GATEWAY")
run("PG+Tok", quote_type="GATEWAY", include_tokenizador=True)
run("PG+Link", quote_type="GATEWAY", include_link_pago=True)
run("PG+Ambos", quote_type="GATEWAY", include_tokenizador=True, include_link_pago=True)
run("LP standalone ambos", quote_type="LINK_PAGO", link_pago_variant="ambos", lp_standalone=True, pg_setup_items=[])
run("LP standalone tok", quote_type="LINK_PAGO", link_pago_variant="tokenizador", lp_standalone=True, pg_setup_items=[])
run("LP legacy ambos", quote_type="LINK_PAGO", link_pago_variant="ambos")
run("VPOS", quote_type="VPOS")
