import { Button } from '../../ui/button';
import { GitBranch, Tag, FileText, MapPin, ArrowRight } from 'lucide-react';
import { sortTree } from './scopeUtils';

// Estructura completa definida en la cotización (Multi Marca / Multi RIF / Multitienda).
export const ScopeTreePhase = ({ scope, onContinue }) => {
  const { tipologia, tree, desglose, total } = scope;
  const byBrand = sortTree(tree).reduce((m, r) => {
    const k = r.marca_name || 'Sin marca';
    m[k] = [...(m[k] || []), r];
    return m;
  }, {});
  return (
    <div className="flex flex-col min-h-0 flex-1 py-2 gap-3" data-testid="multistore-scope-phase">
      <div className="bg-teal-50 border border-teal-200 rounded-lg p-3 shrink-0">
        <p className="text-sm font-semibold text-teal-800 flex items-center gap-1.5"><GitBranch size={15} /> Proyecto <span data-testid="scope-phase-tipologia">{tipologia}</span></p>
        <p className="text-xs text-teal-700 mt-0.5">Estructura tomada de la cotización: {tree.length} RIF(s), {tree.reduce((s, r) => s + (r.stores || []).length, 0)} sucursal(es).</p>
      </div>
      <div className="overflow-y-auto min-h-0 flex-1 border border-slate-200 rounded-lg divide-y" data-testid="scope-phase-tree">
        {Object.entries(byBrand).map(([brand, rifs]) => (
          <div key={brand}>
            <div className="px-3 py-1.5 bg-teal-50/60 text-xs font-bold text-teal-800 flex items-center gap-1.5"><Tag size={12} /> {brand}</div>
            {rifs.map(r => (
              <div key={r.client_id} className="pl-5 pr-3 py-1.5">
                <p className="text-xs font-semibold text-slate-800 flex items-center gap-1.5"><FileText size={12} className="text-indigo-500" /> <span className="font-mono text-slate-500">{r.rif}</span> {r.legal_name}</p>
                {(r.stores || []).map(s => (
                  <div key={s.client_id} className="pl-5 flex items-center gap-2 text-xs text-slate-600 py-0.5" data-testid={`scope-phase-store-${s.client_id}`}>
                    <MapPin size={11} className="text-amber-500" /> {s.name}
                    {desglose && <span className="ml-auto font-semibold text-slate-800">{s.boxes || 0} cajas</span>}
                  </div>
                ))}
              </div>
            ))}
          </div>
        ))}
      </div>
      <div className="flex items-center justify-between shrink-0">
        <p className="text-sm text-slate-700">Total Cajas: <span className="font-bold" data-testid="scope-phase-total">{total}</span>{!desglose && <span className="text-xs text-slate-400"> (carga global)</span>}</p>
        <Button className="bg-blue-600 hover:bg-blue-700 text-white" onClick={onContinue} data-testid="scope-phase-continue-btn">
          Continuar <ArrowRight size={14} className="ml-1.5" />
        </Button>
      </div>
    </div>
  );
};
