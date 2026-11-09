import re
def R(p,a,b):
    s=open(p).read(); assert a in s,(p,a[:60]); s=s.replace(a,b,1); open(p,'w').write(s)
SCOPE_IN='''    # Alcance jerárquico VPOS/MPOS (Grupo → Marcas → RIFs → Sucursales) y patrocinio
    nivel_cotizacion: Optional[str] = None
    grupo_economico_id: Optional[str] = None
    grupo_economico_name: Optional[str] = None
    scope_tree: Optional[List[dict]] = None
    cajas_desglose: Optional[bool] = None
    patrocinador_tipo: Optional[str] = None
    patrocinador_id: Optional[str] = None
    patrocinador_nombre: Optional[str] = None
'''
R('models.py','''    multirif_distribution: Optional[List[dict]] = None
    # Flujo Irregular''','''    multirif_distribution: Optional[List[dict]] = None
'''+SCOPE_IN+'''    tipo_proyecto_inferido: Optional[str] = None
    cotizacion_sucursales: List[dict] = []
    # Flujo Irregular''')
R('routes/quotes.py','''    multirif_distribution: Optional[List[dict]] = None
    # Override del total calculado por el wizard del frontend''','''    multirif_distribution: Optional[List[dict]] = None
'''+SCOPE_IN+'''    # Override del total calculado por el wizard del frontend''')
R('routes/quotes.py','''    # (duplicar+PUT) para que una cotización CORP no se degrade a PYME.
    client_segment: Optional[str] = None
''','''    # (duplicar+PUT) para que una cotización CORP no se degrade a PYME.
    client_segment: Optional[str] = None
'''+SCOPE_IN)
R('routes/quotes.py','''            multirif_distribution=data.multirif_distribution,
            requires_pinpad_config=data.requires_pinpad_config,''','''            multirif_distribution=data.multirif_distribution,
            **compute_scope(data.model_dump()),
            requires_pinpad_config=data.requires_pinpad_config,''')
R('routes/quotes.py','''                if not getattr(pdf_request, "multirif_distribution", None):
                    pdf_request.multirif_distribution = data.multirif_distribution or []
''','''                if not getattr(pdf_request, "multirif_distribution", None):
                    pdf_request.multirif_distribution = data.multirif_distribution or []
                if not data.is_multirif and data.scope_tree:
                    _tree = clean_tree(data.scope_tree)
                    pdf_request.multirif_distribution = to_distribution(_tree, bool(data.cajas_desglose)) if is_multi(_tree) else []
''')
R('routes/quotes.py','''    for field, value in update_fields.items():
        if value is not None:
            update_data[field] = value
''','''    for field, value in update_fields.items():
        if value is not None:
            update_data[field] = value
    if "scope_tree" in update_data:
        update_data.update(compute_scope(update_data))
''')
s=open('routes/quotes.py').read()
i=s.index('\nrouter = APIRouter()')
s=s[:i]+'\nfrom services.quote_scope import compute_scope, clean_tree, to_distribution, is_multi'+s[i:]
open('routes/quotes.py','w').write(s)
R('services/pdf_generator.py','''        if getattr(self.data, 'is_multirif', False):
            self._build_multirif_section(elements)''','''        if getattr(self.data, 'is_multirif', False) or getattr(self.data, 'multirif_distribution', None):
            self._build_multirif_section(elements)''')
s=open('services/pdf_generator.py').read()
a='''        if getattr(self.data, 'is_multirif', False):
            self._build_multirif_section(elements)'''
assert a in s; s=s.replace(a,'''        if getattr(self.data, 'is_multirif', False) or getattr(self.data, 'multirif_distribution', None):
            self._build_multirif_section(elements)''',1); open('services/pdf_generator.py','w').write(s)
print('ok')
