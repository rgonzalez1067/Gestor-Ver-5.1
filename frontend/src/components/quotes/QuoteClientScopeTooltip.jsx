import { Tag, FileText, MapPin } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../ui/tooltip';

const byBrand = (tree) => tree.reduce((m, r) => {
  const k = r.marca_name || 'Sin marca';
  m[k] = [...(m[k] || []), r];
  return m;
}, {});

const ScopeTree = ({ tree }) => (
  <div className="space-y-1.5 max-h-72 overflow-y-auto pr-1">
    {Object.entries(byBrand(tree)).map(([brand, rifs]) => (
      <div key={brand}>
        <p className="flex items-center gap-1 font-semibold text-amber-300"><Tag size={11} /> Marca: {brand}</p>
        {rifs.map((r, i) => (
          <div key={`${r.rif}-${i}`} className="pl-3 mt-0.5">
            <p className="flex items-center gap-1 text-slate-100"><FileText size={10} className="text-sky-300 shrink-0" /> <span className="font-mono text-slate-400">{r.rif}</span> {r.legal_name}</p>
            {(r.stores || []).map((s, j) => (
              <p key={j} className="pl-4 flex items-center gap-1 text-slate-300"><MapPin size={9} className="text-emerald-300 shrink-0" /> {s.is_principal ? `Sede Principal${s.name && s.name !== 'Principal' ? ` · ${s.name}` : ''}` : s.name}</p>
            ))}
          </div>
        ))}
      </div>
    ))}
  </div>
);

// Celda Cliente con árbol jerárquico (Marcas → RIFs → Sucursales) en hover.
export const QuoteClientScopeTooltip = ({ label, tree, quoteId }) => (
  <TooltipProvider delayDuration={100}>
    <Tooltip>
      <TooltipTrigger asChild>
        {label.kind === 'multi' ? (
          <span className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-semibold bg-indigo-50 text-indigo-700 border border-indigo-200 cursor-help" data-testid={`quote-client-varios-rif-${quoteId}`}>
            Varios Rif
          </span>
        ) : (
          <span className="cursor-help underline decoration-dotted decoration-slate-300 underline-offset-2" data-testid={`quote-client-scope-${quoteId}`}>{label.text}</span>
        )}
      </TooltipTrigger>
      <TooltipContent side="top" className="bg-slate-900 text-white text-xs max-w-[380px] border-slate-700 p-3" data-testid={`quote-client-scope-tooltip-${quoteId}`}>
        <p className="font-semibold mb-1.5 text-slate-300 uppercase tracking-wide text-[10px]">Alcance jerárquico de la cotización</p>
        <ScopeTree tree={tree} />
      </TooltipContent>
    </Tooltip>
  </TooltipProvider>
);
