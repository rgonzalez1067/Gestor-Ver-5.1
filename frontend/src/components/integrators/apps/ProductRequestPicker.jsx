import { CERT_STATES } from './appPayload';

// Regla de proyecto: '-'/P/N/A ↔ S (Solicitado) · C ↔ R (Recertificación).
export const toggleRequest = (cur, original) => {
  if (cur === 'S') return original && original !== 'S' ? original : 'N/A';
  if (cur === 'R') return 'C';
  return cur === 'C' ? 'R' : 'S';
};

// Matriz clicable para marcar productos a certificar en un proyecto de Ampliación.
export const ProductRequestPicker = ({ products, base, value, onChange, testid = 'request-matrix' }) => (
  <div data-testid={testid}>
    <div className="grid grid-cols-2 md:grid-cols-3 gap-1.5">
      {products.map((p) => {
        const orig = (base || {})[p.service_id] || 'N/A';
        const cur = value[p.service_id] || orig;
        const st = CERT_STATES[cur] || CERT_STATES['N/A'];
        return (
          <button type="button" key={p.service_id} onClick={() => onChange({ ...value, [p.service_id]: toggleRequest(cur, orig) })}
            className={`flex items-center justify-between gap-2 rounded-md border px-2 py-1.5 text-left text-[11px] transition-colors hover:shadow-sm ${cur !== orig ? 'ring-1 ring-amber-300' : ''} border-slate-200 bg-white`}
            data-testid={`${testid}-cell-${p.service_id}`}>
            <span className="leading-tight text-slate-700">{p.name}</span>
            <span className={`min-w-[34px] rounded border px-1.5 py-0.5 text-center font-bold ${st.color}`}>{st.label}</span>
          </button>
        );
      })}
    </div>
    <p className="mt-1.5 text-[10px] text-slate-500">
      Pulse un producto disponible para marcarlo <b className="text-blue-700">S</b> (Solicitado) o uno certificado para <b className="text-slate-600">R</b> (Recertificación). Pulse de nuevo para revertir.
    </p>
  </div>
);
