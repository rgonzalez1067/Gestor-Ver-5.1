import sys
sys.path.insert(0, '/app/backend')
from PyPDF2 import PdfReader
from services.pdf_generator import TemplateQuotePDFRequest, DynamicQuotePDFGenerator

def item(concepto, tarifa, tc, cajas=10):
    return {"concepto": concepto, "tarifa": tarifa, "cantidad_cajas": cajas, "cantidad_bancos": 1, "tipo_corp": tc}

def run(label, **kw):
    base = dict(cliente_nombre="Corp Demo", cliente_rif="J1", client_segment="CORP", quote_type="VPOS", cantidad_cajas=10,
                integrator_name="I", integrator_app_name="A",
                setup_items=[item("Licencia", 100, "Derecho de Uso")],
                recurring_basic_items=[item("Soporte", 8, "Soporte y Monitoreo")])
    base.update(kw)
    req = TemplateQuotePDFRequest(**base)
    buf = DynamicQuotePDFGenerator(req, None).generate(); buf.seek(0)
    pages = [(p.extract_text() or '') for p in PdfReader(buf).pages]
    pg = next(t for t in pages if 'COSTOS DE IMPLEMENTACI' in t and 'Set-up' in t)
    print('=====', label); print(pg[:900])

run("sin descuento")
run("desc 20/10", descuento_setup=20, descuento_recurrente=10)
run("multirif", is_multirif=True, multirif_distribution=[{"rif": "J1", "boxes": 6}, {"rif": "J2", "boxes": 4}], cantidad_cajas=6)
run("MPOS corp (sin cambio)", quote_type="MPOS", descuento_setup=20)

req = TemplateQuotePDFRequest(cliente_nombre="Corp", cliente_rif="J1", client_segment="CORP", quote_type="VPOS", cantidad_cajas=10, descuento_setup=20, descuento_recurrente=10,
    setup_items=[item("Licencia", 100, "Derecho de Uso"), item("Infra", 5, "Infraestructura")], recurring_basic_items=[item("Soporte", 8, "Soporte y Monitoreo")])
buf = DynamicQuotePDFGenerator(req, None).generate()
open('/tmp/corp.pdf', 'wb').write(buf.getvalue())
