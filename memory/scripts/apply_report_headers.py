import re
B = '/app/backend/'
IMPORT = "from services.report_header import html_with_page_header\n"

def patch(path, pairs, add_import=True):
    p = B + path
    s = open(p).read()
    for old, new in pairs:
        assert s.count(old) >= 1, (path, old)
        s = s.replace(old, new, 1)
    if add_import and IMPORT not in s:
        # después del primer bloque de imports
        idx = s.index("\nfrom ") + 1
        s = s[:idx] + IMPORT + s[idx:]
    open(p, 'w').write(s)

patch('routes/banks.py', [('pdf_bytes = weasyprint.HTML(string=html).write_pdf()',
                           'pdf_bytes = weasyprint.HTML(string=html_with_page_header(html, "Productos por Banco")).write_pdf()')])
patch('routes/services.py', [('pdf_bytes = weasyprint.HTML(string=html).write_pdf()',
                              'pdf_bytes = weasyprint.HTML(string=html_with_page_header(html, "Bancos por Producto")).write_pdf()')])
patch('routes/projects.py', [('pdf_bytes = weasyprint.HTML(string=html).write_pdf()',
                              'pdf_bytes = weasyprint.HTML(string=html_with_page_header(html, "Reporte de Carga y Estatus de Proyectos")).write_pdf()')])
patch('routes/project_reports.py', [('pdf_bytes = weasyprint.HTML(string=html).write_pdf()',
                                     'pdf_bytes = weasyprint.HTML(string=html_with_page_header(html, "Reporte de Avance del Proyecto")).write_pdf()')])
s = open(B + 'routes/sales_reports.py').read()
calls = [m.start() for m in re.finditer(re.escape('pdf_bytes = weasyprint.HTML(string=html).write_pdf()'), s)]
assert len(calls) == 2
s = s.replace('pdf_bytes = weasyprint.HTML(string=html).write_pdf()',
              'pdf_bytes = weasyprint.HTML(string=html_with_page_header(html, "Cotizaciones en Estado Irregular")).write_pdf()', 1)
s = s.replace('pdf_bytes = weasyprint.HTML(string=html).write_pdf()',
              'pdf_bytes = weasyprint.HTML(string=html_with_page_header(html, "Resumen Ejecutivo de Ventas")).write_pdf()', 1)
open(B + 'routes/sales_reports.py', 'w').write(s)
patch('routes/sales_reports.py', [], add_import=True)
# pdf_report: marca consistente
patch('services/pdf_report.py', [('"CRM - Gestor")', '"Gestor - CRM")'), ('# "CRM - Gestor"', '# "Gestor - CRM"')], add_import=False)
print('ok')
