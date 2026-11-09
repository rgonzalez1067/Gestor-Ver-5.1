// Alcance jerárquico VPOS/MPOS (Grupo → Marcas → RIFs → Sucursales) + Tipo de Patrocinio.
export const isScopeType = (qt) => qt === 'VPOS' || qt === 'MPOS';

export const EMPTY_SCOPE = {
  nivel_cotizacion: '', grupo_economico_id: '', grupo_economico_name: '', scope_tree: [], cajas_desglose: true,
  patrocinador_tipo: '', patrocinador_id: '', patrocinador_nombre: '',
};

export const scopePayload = (qd) => (isScopeType(qd.quote_type) ? {
  nivel_cotizacion: qd.nivel_cotizacion || null,
  grupo_economico_id: qd.grupo_economico_id || null,
  grupo_economico_name: qd.grupo_economico_name || null,
  scope_tree: qd.scope_tree || [],
  cajas_desglose: !!qd.cajas_desglose,
  patrocinador_tipo: qd.patrocinador_tipo || null,
  patrocinador_id: qd.patrocinador_id || null,
  patrocinador_nombre: qd.patrocinador_nombre || null,
} : {});

// Distribución para el PDF ("Detalle de Tiendas y Sucursales") cuando hay >1 RIF o >1 tienda.
export const scopeDistribution = (qd) => {
  const tree = isScopeType(qd.quote_type) ? (qd.scope_tree || []) : [];
  const stores = tree.reduce((s, r) => s + (r.stores || []).length, 0);
  if (tree.length < 2 && stores < 2) return [];
  return tree.map(r => {
    const st = (r.stores || []).map(s => ({ name: s.name, boxes: qd.cajas_desglose ? (parseInt(s.boxes) || 0) : 0 }));
    return {
      client_id: r.client_id, rif: r.rif, marca_name: r.marca_name,
      client_name: r.marca_name ? `${r.marca_name} · ${r.legal_name}` : r.legal_name,
      boxes: st.reduce((a, s) => a + s.boxes, 0), stores: st,
    };
  });
};

export const inferTipologia = (tree = []) => {
  if (!tree.length) return '';
  const marcas = new Set(tree.map(r => r.marca_id).filter(Boolean));
  const stores = tree.reduce((s, r) => s + Math.max((r.stores || []).length, 1), 0);
  if (marcas.size > 1) return 'Multi Marca';
  if (tree.length > 1) return 'Multi RIF';
  return stores > 1 ? 'Multitienda' : 'Monotienda';
};

export const isScopeValid = (qd) => {
  if (!isScopeType(qd.quote_type)) return true;
  const tree = qd.scope_tree || [];
  if (!tree.length || tree.some(r => !(r.stores || []).length)) return false;
  if (qd.patrocinador_tipo === 'BANCO') return !!qd.sponsoring_bank_id;
  if (qd.patrocinador_tipo === 'CLIENTE') return !!qd.patrocinador_id;
  return false;
};

// Al editar: usa el alcance guardado o reconstruye uno mínimo (RIF + tienda) para cotizaciones previas.
export const scopeFromQuote = (quote, clients) => {
  if (!isScopeType(quote.quote_type)) return {};
  if ((quote.scope_tree || []).length) {
    return {
      nivel_cotizacion: quote.nivel_cotizacion || 'RIF', grupo_economico_id: quote.grupo_economico_id || '',
      grupo_economico_name: quote.grupo_economico_name || '', scope_tree: quote.scope_tree,
      cajas_desglose: !!quote.cajas_desglose, patrocinador_tipo: quote.patrocinador_tipo || '',
      patrocinador_id: quote.patrocinador_id || '', patrocinador_nombre: quote.patrocinador_nombre || '',
    };
  }
  const c = (clients || []).find(x => x.client_id === quote.client_id);
  if (!c) return { ...EMPTY_SCOPE };
  const p = c.is_branch ? ((clients || []).find(x => x.client_id === c.parent_client_id) || c) : c;
  const sponsored = !!quote.sponsored_implementation;
  return {
    ...EMPTY_SCOPE, nivel_cotizacion: 'RIF', cajas_desglose: false,
    scope_tree: [{ client_id: p.client_id, rif: p.rif, legal_name: p.legal_name, marca_id: p.marca_id || null, marca_name: p.marca_name || '',
      stores: [{ client_id: c.client_id, name: c.sucursal || 'Principal', is_principal: !c.is_branch, boxes: 0 }] }],
    patrocinador_tipo: sponsored ? 'BANCO' : 'CLIENTE',
    patrocinador_id: sponsored ? (quote.sponsoring_bank_id || '') : p.client_id,
    patrocinador_nombre: sponsored ? (quote.sponsoring_bank_name || '') : (p.legal_name || ''),
  };
};
