import { Label } from '../ui/label';

const YesNo = ({ value, onChange, testid }) => (
  <div className="flex gap-1.5" role="radiogroup">
    {[true, false].map((v) => (
      <button
        key={String(v)}
        type="button"
        role="radio"
        aria-checked={value === v}
        onClick={() => onChange(v)}
        data-testid={`${testid}-${v ? 'yes' : 'no'}`}
        className={`px-3 py-1.5 rounded-md text-xs font-semibold border transition-colors ${
          value === v
            ? (v ? 'bg-brand-blue-600 text-white border-brand-blue-700 shadow-sm' : 'bg-slate-700 text-white border-slate-800 shadow-sm')
            : 'bg-white text-slate-700 border-slate-300 hover:border-slate-400'
        }`}
      >
        {v ? 'Sí' : 'No'}
      </button>
    ))}
  </div>
);

// Payment Gateway: servicios adicionales que anexan sus páginas de tarifas al PDF.
export const PgAdditionalServicesToggles = ({ quoteData, setQuoteData }) => (
  <div className="flex-shrink-0 border-l border-slate-200 pl-4 flex gap-6" data-testid="pg-additional-services-block">
    <div>
      <Label className="text-sm font-semibold text-slate-800 block mb-2">¿Se incluye Tokenizador?</Label>
      <p className="text-[11px] text-slate-500 mb-2 leading-tight max-w-[200px]">Anexa la sección de tarifas del Tokenizador al PDF.</p>
      <YesNo value={!!quoteData.include_tokenizador} testid="pg-include-tokenizador"
        onChange={(v) => setQuoteData({ ...quoteData, include_tokenizador: v })} />
    </div>
    <div>
      <Label className="text-sm font-semibold text-slate-800 block mb-2">¿Se incluye Link de Pago?</Label>
      <p className="text-[11px] text-slate-500 mb-2 leading-tight max-w-[200px]">Anexa la sección de tarifas de Link de Pago al PDF.</p>
      <YesNo value={!!quoteData.include_link_pago} testid="pg-include-link-pago"
        onChange={(v) => setQuoteData({ ...quoteData, include_link_pago: v })} />
    </div>
  </div>
);

const LP_SERVICES = { link_pago: ['Link de Pago'], tokenizador: ['Tokenizador'], ambos: ['Link de Pago', 'Tokenizador'] };

// Link de Pago / Tokenizador para clientes con Payment Gateway activo: sin conceptos PG.
export const LpStandaloneSummary = ({ variant, onChangeVariant }) => (
  <div className="bg-white rounded-lg p-5 border mt-4" data-testid="lp-standalone-summary">
    <h3 className="font-semibold text-lg text-slate-800 mb-2">Servicios a cotizar</h3>
    <p className="text-sm text-slate-500 mb-4">
      Cliente con Payment Gateway activo: el documento contendrá únicamente las tarifas de los servicios seleccionados, sin conceptos ni montos de Payment Gateway.
    </p>
    <div className="flex flex-wrap items-center gap-2">
      {(LP_SERVICES[variant] || LP_SERVICES.link_pago).map((s) => (
        <span key={s} className="px-3 py-1 rounded-full text-xs font-semibold bg-blue-50 text-blue-700 border border-blue-200" data-testid={`lp-standalone-service-${s.replace(/\s/g, '-').toLowerCase()}`}>{s}</span>
      ))}
      <button type="button" onClick={onChangeVariant} className="text-xs text-brand-blue-600 underline ml-2" data-testid="lp-standalone-change-variant">Cambiar selección</button>
    </div>
  </div>
);
