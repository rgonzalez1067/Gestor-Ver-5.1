B = '/app/backend/services/'
for f, anchor in [('transfer_note_pdf.py', '    buffer = io.BytesIO()\n    now = datetime.now(timezone.utc)\n'),
                  ('hoja_ruta_pdf.py', None)]:
    p = B + f
    s = open(p).read()
    if anchor is None:
        i = s.index('def generate_nota_entrega_pdf(')
        j = s.index('    """', s.index('):', i))  # docstring start
        j2 = s.index('"""', j + 7) + 3
        anchor_pos = s.index('\n', j2) + 1
        s = s[:anchor_pos] + '    from services.report_header import logo_path_or_none\n    logo_path = logo_path if (logo_path and os.path.exists(logo_path)) else logo_path_or_none()\n' + s[anchor_pos:]
    else:
        assert s.count(anchor) == 1
        s = s.replace(anchor, '    from services.report_header import logo_path_or_none\n    logo_path = logo_path if (logo_path and os.path.exists(logo_path)) else logo_path_or_none()\n' + anchor)
    open(p, 'w').write(s)
print('ok')
