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

const k = (s) => (s || '').trim().toLowerCase();
// Orden de estructura: Marca (A-Z, sin marca al final) → RIF → Principal y sucursales.
export const sortTree = (tree = []) => tree
  .map(r => ({ ...r, stores: [...(r.stores || [])].sort((a, b) => (!!b.is_principal - !!a.is_principal) || k(a.name).localeCompare(k(b.name), 'es')) }))
  .sort((a, b) => (!a.marca_name - !b.marca_name) || k(a.marca_name).localeCompare(k(b.marca_name), 'es') || k(a.legal_name).localeCompare(k(b.legal_name), 'es'));

// Distribución para el PDF ("Detalle de Tiendas y Sucursales") cuando hay >1 RIF o >1 tienda.
export const scopeDistribution = (qd) => {
  const tree = sortTree(isScopeType(qd.quote_type) ? (qd.scope_tree || []) : []);
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

// Entidades de una cotización (cualquier tipo) normalizadas: [{rif, legal_name, marca_name, stores:[{name, is_principal}]}]
export const quoteEntityTree = (quote, clients = []) => {
  const byId = (id) => clients.find(c => c.client_id === id);
  if ((quote.scope_tree || []).length) {
    return sortTree(quote.scope_tree).map(r => ({ rif: r.rif, legal_name: r.legal_name, marca_name: r.marca_name || '', stores: r.stores || [] }));
  }
  if ((quote.multirif_distribution || []).length) {
    return quote.multirif_distribution.map(r => {
      const c = byId(r.client_id) || {};
      return { rif: r.rif || c.rif, legal_name: c.legal_name || r.client_name, marca_name: r.marca_name || c.marca_name || '',
        stores: (r.stores || []).map(s => ({ name: s.name, is_principal: false })) };
    });
  }
  const c = byId(quote.client_id);
  if (!c) return [];
  const p = c.is_branch ? (byId(c.parent_client_id || c.parent_id) || c) : c;
  const branchStores = (quote.branch_details || []).filter(b => b.store_name).map(b => ({ name: b.store_name, is_principal: false }));
  const stores = branchStores.length > 1 ? branchStores : (c.is_branch ? [{ name: c.sucursal, is_principal: false }] : []);
  return [{ rif: p.rif || c.rif, legal_name: p.legal_name || c.legal_name, marca_name: p.marca_name || '', stores }];
};

// Texto de la columna Cliente: Varios Rif | Razón Social (Sucursal) | Razón Social (N sucursales) | Razón Social
export const quoteClientLabel = (tree) => {
  if (tree.length > 1) return { text: 'Varios Rif', kind: 'multi' };
  const r = tree[0];
  if (!r) return null;
  const stores = r.stores || [];
  if (stores.length > 1) return { text: `${r.legal_name} (${stores.length} sucursales)`, kind: 'stores' };
  if (stores.length === 1 && !stores[0].is_principal && stores[0].name && stores[0].name !== 'Principal') {
    return { text: `${r.legal_name} (${stores[0].name})`, kind: 'branch' };
  }
  return { text: r.legal_name, kind: 'single' };
};

// Sucursal beneficiaria para la portada PDF cuando el alcance es 1 RIF + 1 sucursal (no principal).
export const scopeSingleBranchName = (qd, client) => {
  const tree = isScopeType(qd.quote_type) ? (qd.scope_tree || []) : [];
  if (tree.length === 1 && (tree[0].stores || []).length === 1) {
    const s = tree[0].stores[0];
    return s.is_principal ? '' : (s.name || '');
  }
  return !tree.length && client?.is_branch ? (client.sucursal || '') : '';
};
