p = '/app/backend/services/pdf_generator.py'
s = open(p).read()
def rep(old, new):
    global s
    assert s.count(old) == 1, old[:80]
    s = s.replace(old, new)

rep('''        grand_total = total_setup + total_recurring
        
        # Construir tabla: Header con agrupación
        # Fila 0 (encabezado principal):''', '''        grand_total = total_setup + total_recurring

        # VPOS / VPOS MultiRIF Corp: montos netos (post-descuento) + columna Costo Unitario por Caja.
        unit_mode = (self.data.quote_type or '').upper() == 'VPOS'
        _sp = (getattr(self.data, 'descuento_setup', 0) or 0) or (getattr(self.data, 'descuento', 0) or 0)
        _rp = (getattr(self.data, 'descuento_recurrente', 0) or 0) or (getattr(self.data, 'descuento', 0) or 0)
        net_applied = unit_mode and (_sp > 0 or _rp > 0)
        if unit_mode:
            show_setup = {c: v * (1 - _sp / 100.0) for c, v in setup_by_corp.items()}
            show_rec = {c: v * (1 - _rp / 100.0) for c, v in recurring_by_corp.items()}
        else:
            show_setup, show_rec = dict(setup_by_corp), dict(recurring_by_corp)
        show_total_setup = sum(show_setup.values())
        show_total_rec = sum(show_rec.values())
        show_by_col = {c: show_setup[c] + show_rec[c] for c in CORP_COLUMNS}
        show_grand = show_total_setup + show_total_rec
        if getattr(self.data, 'is_multirif', False) and self.data.multirif_distribution:
            total_cajas = sum(int(d.get('boxes') or 0) for d in self.data.multirif_distribution)
        else:
            total_cajas = int(self.data.cantidad_cajas or 0)
        total_cajas = total_cajas or 1
        
        # Construir tabla: Header con agrupación
        # Fila 0 (encabezado principal):''')

old_rows = s[s.index('''        # Data rows
        row_setup = [
            Paragraph("Set-up", label_style),'''):s.index('''        table_data = [row_header, row_subheader, row_setup, row_recurring, row_total]''')]
new_rows = old_rows
for a, b in [("setup_by_corp[", "show_setup["), ("recurring_by_corp[", "show_rec["), ("total_by_col[", "show_by_col["),
             ("${total_setup:,.2f}", "${show_total_setup:,.2f}"), ("${total_recurring:,.2f}", "${show_total_rec:,.2f}"),
             ("${grand_total:,.2f}", "${show_grand:,.2f}")]:
    new_rows = new_rows.replace(a, b)
s = s.replace(old_rows, new_rows)

rep('''        table_data = [row_header, row_subheader, row_setup, row_recurring, row_total]

        col_widths = [78, 82, 82, 88, 88, 72]
        table = Table(table_data, colWidths=col_widths)''', '''        if unit_mode:
            row_header.append(Paragraph("<b>Costo Unitario<br/>por Caja</b>", subheader_style))
            row_subheader.append('')
            row_setup.append(Paragraph(f"${show_total_setup / total_cajas:,.2f}", cell_style))
            row_recurring.append(Paragraph(f"${show_total_rec / total_cajas:,.2f}", cell_style))
            row_total.append(Paragraph("<b>-</b>", ParagraphStyle('CorpUnitTotal', fontName='Helvetica-Bold', fontSize=9, textColor=colors.white, alignment=1)))

        table_data = [row_header, row_subheader, row_setup, row_recurring, row_total]

        col_widths = [66, 72, 72, 76, 76, 68, 74] if unit_mode else [78, 82, 82, 88, 88, 72]
        table = Table(table_data, colWidths=col_widths)''')
rep('''            ('BACKGROUND', (5, 4), (5, 4), COLOR_AMARILLO),
            ('TEXTCOLOR', (5, 4), (5, 4), colors.HexColor("#1E293B")),
''', '''            ('BACKGROUND', (5, 4), (5, 4), COLOR_AMARILLO),
            ('TEXTCOLOR', (5, 4), (5, 4), colors.HexColor("#1E293B")),
        ] + ([('SPAN', (6, 0), (6, 1)), ('BACKGROUND', (6, 0), (6, 1), self.COLOR_AZUL)] if unit_mode else []) + [
''')
rep('''        nota_style = ParagraphStyle('CorpNota', fontName='Helvetica', fontSize=8, textColor=colors.HexColor("#DC2626"), leading=10)
        elements.append(Paragraph("Montos no incluyen IVA", nota_style))
        elements.append(Spacer(1, 8))
''', '''        nota_style = ParagraphStyle('CorpNota', fontName='Helvetica', fontSize=8, textColor=colors.HexColor("#DC2626"), leading=10)
        elements.append(Paragraph("Montos no incluyen IVA", nota_style))
        elements.append(Spacer(1, 8))
        if net_applied:
            elements.append(Paragraph("Montos con descuento aplicado", ParagraphStyle(
                'CorpNotaDesc', fontName='Helvetica-Bold', fontSize=8, textColor=colors.HexColor('#16A34A'), leading=10)))
            elements.append(Spacer(1, 8))
''')
open(p, 'w').write(s)
print('ok')
