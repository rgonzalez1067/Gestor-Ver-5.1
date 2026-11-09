import { useState, useEffect, useMemo, useRef } from 'react';
import { Label } from '../../ui/label';
import { Layers } from 'lucide-react';
import api from '../../../utils/api';
import { EntityChecklist } from './EntityChecklist';
import { StoresBoxesGrid } from './StoresBoxesGrid';
import { inferTipologia } from './scopeUtils';

const LEVELS = [['GRUPO', 'Grupo Económico'], ['MARCA', 'Marca'], ['RIF', 'RIF']];

const fetchStores = async (rifId) => {
  const { data } = await api.get(`/clients/${rifId}/branches`);
  const p = data.principal || {};
  return [{ client_id: p.client_id || rifId, name: p.sucursal || 'Principal', is_principal: true },
    ...(data.branches || []).map(b => ({ client_id: b.client_id, name: b.sucursal || b.fantasy_name, is_principal: false }))];
};

// value: {nivel_cotizacion, grupo_economico_id, grupo_economico_name, scope_tree, cajas_desglose}
export const QuoteScopeSelector = ({ value, onChange, clients }) => {
  const init = value.scope_tree || [];
  const [nivel, setNivel] = useState(value.nivel_cotizacion || '');
  const [groups, setGroups] = useState([]);
  const [brands, setBrands] = useState([]);
  const [groupId, setGroupId] = useState(value.grupo_economico_id ? [value.grupo_economico_id] : []);
  const [brandIds, setBrandIds] = useState([...new Set(init.map(r => r.marca_id).filter(Boolean))]);
  const [rifIds, setRifIds] = useState(init.map(r => r.client_id));
  const [rifInfo, setRifInfo] = useState(() => Object.fromEntries(init.map(r => [r.client_id, r])));
  const [storesByRif, setStoresByRif] = useState({});
  const [picked, setPicked] = useState(() => Object.fromEntries(init.map(r => [r.client_id, (r.stores || []).map(s => s.client_id)])));
  const [boxes, setBoxes] = useState(() => Object.fromEntries(init.flatMap(r => (r.stores || []).map(s => [s.client_id, s.boxes]))));
  const [desglose, setDesglose] = useState(value.cajas_desglose ?? true);
  const brandRifCache = useRef({});
  const [brandRifs, setBrandRifs] = useState({});

  useEffect(() => {
    api.get('/grupos-economicos').then(r => setGroups(r.data || [])).catch(() => {});
    api.get('/marcas').then(r => setBrands(r.data || [])).catch(() => {});
  }, []);

  // RIFs de las marcas seleccionadas (niveles GRUPO/MARCA)
  useEffect(() => {
    brandIds.forEach(bid => {
      if (brandRifCache.current[bid]) return;
      brandRifCache.current[bid] = true;
      api.get(`/marcas/${bid}/rifs`).then(r => setBrandRifs(p => ({ ...p, [bid]: r.data || [] }))).catch(() => {});
    });
  }, [brandIds]);

  // Sucursales de los RIFs seleccionados
  useEffect(() => {
    rifIds.forEach(id => {
      if (storesByRif[id]) return;
      setStoresByRif(p => ({ ...p, [id]: [] }));
      fetchStores(id).then(stores => {
        setStoresByRif(p => ({ ...p, [id]: stores }));
        setPicked(p => (p[id] ? p : { ...p, [id]: stores.map(s => s.client_id) }));
      }).catch(() => {});
    });
  }, [rifIds]); // eslint-disable-line react-hooks/exhaustive-deps

  const brandItems = useMemo(() => brands
    .filter(b => nivel !== 'GRUPO' || (groupId[0] && b.group_id === groupId[0]))
    .map(b => ({ id: b.brand_id, label: b.name, sub: `${b.rif_count} RIF` })), [brands, nivel, groupId]);
  const brandName = (id) => brands.find(b => b.brand_id === id)?.name || '';

  const rifItems = useMemo(() => {
    if (nivel === 'RIF') {
      return (clients || []).filter(c => !c.is_branch && c.rif)
        .map(c => ({ id: c.client_id, label: c.legal_name || c.fantasy_name, sub: c.rif, marca_id: c.marca_id, marca_name: c.marca_name, rif: c.rif }));
    }
    return brandIds.flatMap(bid => (brandRifs[bid] || []).map(r => ({
      id: r.client_id, label: r.legal_name, sub: r.rif, group: brandName(bid), marca_id: bid, marca_name: brandName(bid), rif: r.rif,
    })));
  }, [nivel, clients, brandIds, brandRifs, brands]); // eslint-disable-line react-hooks/exhaustive-deps

  // Emitir árbol
  useEffect(() => {
    const meta = Object.fromEntries(rifItems.map(i => [i.id, i]));
    const tree = rifIds.map(id => {
      const m = meta[id] || rifInfo[id] || {};
      const stores = (storesByRif[id]?.length ? storesByRif[id] : (rifInfo[id]?.stores || []))
        .filter(s => (picked[id] || []).includes(s.client_id))
        .map(s => ({ ...s, boxes: parseInt(boxes[s.client_id]) || 0 }));
      return { client_id: id, rif: m.rif || m.sub || '', legal_name: m.legal_name || m.label || '', marca_id: m.marca_id || null, marca_name: m.marca_name || '', stores };
    });
    const g = groups.find(x => x.group_id === groupId[0]);
    const total = tree.reduce((s, r) => s + r.stores.reduce((a, st) => a + st.boxes, 0), 0);
    onChange({
      nivel_cotizacion: nivel || null, grupo_economico_id: nivel === 'GRUPO' ? (groupId[0] || null) : null,
      grupo_economico_name: nivel === 'GRUPO' ? (g?.name || value.grupo_economico_name || null) : null,
      scope_tree: tree, cajas_desglose: desglose, total,
    });
  }, [nivel, groupId, rifIds, picked, boxes, desglose, storesByRif, rifItems, groups]); // eslint-disable-line react-hooks/exhaustive-deps

  const changeNivel = (n) => {
    setNivel(n); setGroupId([]); setBrandIds([]); setRifIds([]); setPicked({}); setRifInfo({});
  };
  const changeGroup = (ids) => { setGroupId(ids); setBrandIds([]); setRifIds([]); };
  const changeBrands = (ids) => {
    setBrandIds(ids);
    const valid = new Set(ids.flatMap(b => (brandRifs[b] || []).map(r => r.client_id)));
    setRifIds(prev => prev.filter(id => valid.has(id)));
  };
  const total = rifIds.reduce((s, id) => s + (picked[id] || []).reduce((a, sid) => a + (parseInt(boxes[sid]) || 0), 0), 0);
  const gridRifs = rifIds.map(id => {
    const m = rifItems.find(i => i.id === id) || rifInfo[id] || {};
    return { client_id: id, rif: m.sub || m.rif, legal_name: m.label || m.legal_name, marca_name: m.marca_name, stores: storesByRif[id]?.length ? storesByRif[id] : (rifInfo[id]?.stores || []) };
  });

  return (
    <div className="mt-4 p-4 bg-white border border-indigo-200 rounded-lg space-y-3" data-testid="quote-scope-selector">
      <div className="flex items-center gap-3 flex-wrap">
        <Label className="text-sm font-semibold text-slate-800 flex items-center gap-1.5"><Layers size={15} className="text-indigo-600" /> ¿Cuál es el nivel de la Cotización? <span className="text-red-500">*</span></Label>
        <div className="flex gap-1.5" role="radiogroup">
          {LEVELS.map(([k, l]) => (
            <button key={k} type="button" role="radio" aria-checked={nivel === k} onClick={() => changeNivel(k)} data-testid={`scope-level-${k}`}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold border transition-colors ${nivel === k ? 'bg-indigo-600 text-white border-indigo-700' : 'bg-white text-slate-700 border-slate-300 hover:border-indigo-400'}`}>{l}</button>
          ))}
        </div>
      </div>
      {nivel && (
        <div className={`grid grid-cols-1 gap-3 ${nivel === 'GRUPO' ? 'lg:grid-cols-3' : nivel === 'MARCA' ? 'lg:grid-cols-2' : ''}`}>
          {nivel === 'GRUPO' && (
            <EntityChecklist title="Grupo Económico" multiple={false} testId="scope-groups" selected={groupId} onChange={changeGroup}
              items={groups.map(g => ({ id: g.group_id, label: g.name, sub: `${g.brands_count ?? 0} marcas` }))} />
          )}
          {(nivel === 'GRUPO' || nivel === 'MARCA') && (
            <EntityChecklist title="Marcas" testId="scope-brands" selected={brandIds} onChange={changeBrands} items={brandItems}
              emptyText={nivel === 'GRUPO' && !groupId[0] ? 'Seleccione un grupo.' : 'Sin marcas.'} />
          )}
          <EntityChecklist title="RIFs / Razón Social" testId="scope-rifs" selected={rifIds} onChange={setRifIds} items={rifItems}
            grouped={nivel !== 'RIF' && brandIds.length > 1} emptyText={nivel === 'RIF' ? 'Sin RIFs.' : 'Seleccione al menos una marca.'} />
        </div>
      )}
      {rifIds.length > 0 && (
        <StoresBoxesGrid rifs={gridRifs} picked={picked} onPick={(rid, ids) => setPicked(p => ({ ...p, [rid]: ids }))}
          boxes={boxes} onBoxes={(sid, n) => setBoxes(p => ({ ...p, [sid]: n }))} desglose={desglose} onDesglose={setDesglose} total={total} />
      )}
      {(value.scope_tree || []).length > 0 && (
        <p className="text-xs text-slate-600" data-testid="scope-tipologia">
          Tipología del proyecto: <span className="font-semibold text-teal-700 bg-teal-50 border border-teal-200 px-2 py-0.5 rounded" data-testid="scope-tipologia-value">{inferTipologia(value.scope_tree)}</span>
        </p>
      )}
    </div>
  );
};
