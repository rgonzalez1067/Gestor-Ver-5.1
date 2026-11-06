B = '/app/backend/'
IMP = "from services.report_header import draw_page_header\n"

def patch(path, pairs):
    p = B + path
    s = open(p).read()
    for old, new in pairs:
        assert s.count(old) == 1, (path, old[:80], s.count(old))
        s = s.replace(old, new)
    if IMP not in s:
        idx = s.index("\nfrom ") + 1
        s = s[:idx] + IMP + s[idx:]
    open(p, 'w').write(s)

patch('routes/integrators.py', [
    ("""    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
""", """    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=72)
    elements = []
    styles = getSampleStyleSheet()
"""),
    ("""    elements.append(table)
    
    doc.build(elements)
    buffer.seek(0)
""", """    elements.append(table)

    def _hdr(canvas, doc_):
        draw_page_header(canvas, doc_, "Reporte de Integradores")
    doc.build(elements, onFirstPage=_hdr, onLaterPages=_hdr)
    buffer.seek(0)
"""),
])
patch('routes/economic_groups.py', [
    ("""        topMargin=16 * mm, bottomMargin=16 * mm,
        title=f"Grupo Económico - {group.get('name', '')}",""", """        topMargin=26 * mm, bottomMargin=16 * mm,
        title=f"Grupo Económico - {group.get('name', '')}","""),
    ("""        canvas.drawString(18 * mm, 10 * mm, "Megasoft · Grupo Económico")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Página {doc_.page}")
        canvas.restoreState()
""", """        canvas.drawString(18 * mm, 10 * mm, "Megasoft · Grupo Económico")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Página {doc_.page}")
        canvas.restoreState()
        draw_page_header(canvas, doc_, f"Grupo Económico - {group.get('name', '')}")
"""),
])
patch('routes/implementer_report.py', [
    ("""        topMargin=16 * mm, bottomMargin=16 * mm,
        title="Reporte de Gestión de Implementadores",""", """        topMargin=26 * mm, bottomMargin=16 * mm,
        title="Reporte de Gestión de Implementadores","""),
    ("""        canvas.drawString(18 * mm, 10 * mm, "Megasoft · Reporte de Gestión de Implementadores")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Página {doc_.page}")
        canvas.restoreState()
""", """        canvas.drawString(18 * mm, 10 * mm, "Megasoft · Reporte de Gestión de Implementadores")
        canvas.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Página {doc_.page}")
        canvas.restoreState()
        draw_page_header(canvas, doc_, "Reporte de Gestión de Implementadores")
"""),
])
patch('services/temporary_assignment_pdf.py', [
    ("""        topMargin=2 * cm, bottomMargin=2 * cm,
        leftMargin=1.8 * cm, rightMargin=1.8 * cm,
    )""", """        topMargin=2.6 * cm, bottomMargin=2 * cm,
        leftMargin=1.8 * cm, rightMargin=1.8 * cm,
    )"""),
    ("""    doc.build(story)
    return buffer.getvalue()""", """    def _hdr(canvas, doc_):
        if doc_.page > 1:
            draw_page_header(canvas, doc_, "Asignación Temporal de Inventario")
    doc.build(story, onFirstPage=_hdr, onLaterPages=_hdr)
    return buffer.getvalue()"""),
])
print('ok')
