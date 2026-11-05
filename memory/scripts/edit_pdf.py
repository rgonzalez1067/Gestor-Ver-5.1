p='/app/backend/services/pdf_generator.py'
s=open(p).read()
def rep(old,new):
    global s
    assert s.count(old)==1, old[:80]
    s=s.replace(old,new)
rep('''    link_pago_variant: str = "link_pago"  # link_pago | tokenizador | ambos
''','''    link_pago_variant: str = "link_pago"  # link_pago | tokenizador | ambos
    include_tokenizador: bool = False  # GATEWAY: anexa tarifas del Tokenizador
    include_link_pago: bool = False    # GATEWAY: anexa tarifas de Link de Pago
    lp_standalone: bool = False        # LINK_PAGO sin conceptos de Payment Gateway
''')
rep('''        if self.data.quote_type == 'GATEWAY':
            return self.generate_pg()
        if self.data.client_segment''','''        if self.data.quote_type == 'GATEWAY':
            files = []
            if self.data.include_tokenizador:
                files.append(self._anexo_path("tokenizador_anexo.pdf"))
            if self.data.include_link_pago:
                files.append(self._anexo_path("link_pago_anexo.pdf"))
            pg_buffer = self.generate_pg()
            return self._insert_anexos_before_terms(pg_buffer, files) if files else pg_buffer
        if self.data.client_segment''')
start=s.index('    def _generate_link_pago(self):')
end=s.index('    def generate_vpos(self):')
s=s[:start]+'''    @staticmethod
    def _anexo_path(name: str) -> str:
        import os
        return os.path.join(os.path.dirname(__file__), "..", "static", "anexos", name)

    def _generate_link_pago(self):
        """Link de Pago / Tokenizador: reutiliza el flujo PG e intercala las páginas
        de tarifas antes de los Términos. Con `lp_standalone` (clientes con
        Payment Gateway activo) se omiten todos los conceptos de PG."""
        variant = (getattr(self.data, "link_pago_variant", None) or "link_pago").lower()
        if variant == "tokenizador":
            files = [self._anexo_path("tokenizador_anexo.pdf")]
        elif variant == "ambos":
            files = [self._anexo_path("link_pago_anexo.pdf"), self._anexo_path("tokenizador_anexo.pdf")]
        else:
            files = [self._anexo_path("link_pago_anexo.pdf")]
        self._link_pago_mode = True
        self._lp_standalone = bool(getattr(self.data, "lp_standalone", False))
        try:
            pg_buffer = self.generate_pg()
        finally:
            self._link_pago_mode = False
            self._lp_standalone = False
        return self._insert_anexos_before_terms(pg_buffer, files)

    def _insert_anexos_before_terms(self, pg_buffer, anexo_files):
        """Inserta la 1ra página de cada anexo justo antes de la última página (Términos)."""
        try:
            import os
            import io as _io
            from PyPDF2 import PdfReader, PdfWriter
            pages = []
            for ap_path in anexo_files:
                if not os.path.exists(ap_path):
                    logger.warning(f"[pdf_generator] Anexo no encontrado: {ap_path}")
                    continue
                pages.append(PdfReader(ap_path).pages[0])
            if not pages:
                return pg_buffer
            pg_buffer.seek(0)
            base_pages = list(PdfReader(pg_buffer).pages)
            insert_idx = max(0, len(base_pages) - 1)
            writer = PdfWriter()
            for i, p in enumerate(base_pages):
                if i == insert_idx:
                    for ap in pages:
                        writer.add_page(ap)
                writer.add_page(p)
            out = _io.BytesIO()
            writer.write(out)
            out.seek(0)
            return out
        except Exception as e:
            logger.error(f"[pdf_generator] Error intercalando anexos Link de Pago/Tokenizador: {e}")
            pg_buffer.seek(0)
            return pg_buffer

    def _lp_standalone_body(self):
        """Cuerpo del PDF Link de Pago/Tokenizador sin Payment Gateway."""
        variant = (self.data.link_pago_variant or "link_pago").lower()
        servicios = {"tokenizador": ["Tokenizador"], "ambos": ["Link de Pago", "Tokenizador"]}.get(variant, ["Link de Pago"])
        integrator_text = f'el aplicativo <b>{self.data.integrator_app_name}</b> desarrollado por <b>{self.data.integrator_name}</b>' if self.data.integrator_name and self.data.integrator_name != 'Sin integrador por el momento' else 'su plataforma de e-commerce'
        nombres = " y ".join(f"<b>{x}</b>" for x in servicios)
        els = [Paragraph(f"""
        Por medio de la presente, nos complace presentarle nuestra propuesta comercial para incorporar el servicio de
        {nombres} sobre su Payment Gateway activo en el Merchant Server, integrado con {integrator_text}.
        """, self.styles['TextoNormal']), Spacer(1, 15),
            Paragraph("SERVICIOS COTIZADOS", self.styles['SeccionHeader']), Spacer(1, 8)]
        t = Table([["N°", "Servicio"]] + [[str(i), x] for i, x in enumerate(servicios, 1)], colWidths=[40, 450])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), self.COLOR_AZUL),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (0, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E0E0E0")),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ]))
        els.append(t)
        els.append(Spacer(1, 10))
        els.append(Paragraph("Las tarifas de cada servicio se detallan en las páginas siguientes.", self.styles['TextoNormal']))
        return els

'''+s[end:]
rep('''        if getattr(self, "_link_pago_mode", False):
            pg_subtitle = "Payment Gateway · Link de Pagos"''','''        standalone = getattr(self, "_lp_standalone", False)
        if standalone:
            pg_subtitle = {"tokenizador": "Tokenizador", "ambos": "Link de Pago · Tokenizador"}.get(
                (self.data.link_pago_variant or "").lower(), "Link de Pago")
        elif getattr(self, "_link_pago_mode", False):
            pg_subtitle = "Payment Gateway · Link de Pagos"''')
anchor='''        integrator_text = f'el aplicativo <b>{self.data.integrator_app_name}</b> desarrollado por <b>{self.data.integrator_name}</b>' if self.data.integrator_name and self.data.integrator_name != 'Sin integrador por el momento' else 'su plataforma de e-commerce'
        carta_body = f"""
        Por medio de la presente, nos complace presentarle nuestra propuesta comercial para la implementación 
        del servicio de <b>Payment Gateway</b>'''
rep(anchor,'''        if standalone:
            elements.extend(self._lp_standalone_body())
            if has_features(self.data.notes):
                elements.append(PageBreak())
                elements.extend(features_flowables(self.data.notes))
            elements.append(PageBreak())
            elements.extend(self._pg_terms_elements())
            doc.build(elements)
            self.buffer.seek(0)
            return self.buffer

'''+anchor)
t0=s.index('''        # ==================== PÁGINA 5: TÉRMINOS DE LA COTIZACIÓN ====================''', s.index('    def generate_pg(self):'))
t1=s.index('''        doc.build(elements)''', t0)
terms_block=s[t0:t1]
s=s[:t0]+'''        elements.extend(self._pg_terms_elements())

'''+s[t1:]
body=terms_block.replace('elements.append(','els.append(')
method='''    def _pg_terms_elements(self):
        els = []
'''+body+'''        return els

    def generate_pg(self):'''
s=s.replace('    def generate_pg(self):',method,1)
open(p,'w').write(s)
print("done")
