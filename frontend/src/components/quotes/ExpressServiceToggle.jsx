const OptionButton = ({ active, onClick, testId, activeClass, children }) => (
  <button
    type="button"
    role="radio"
    aria-checked={active}
    onClick={onClick}
    data-testid={testId}
    className={`px-3 py-1.5 rounded-md text-xs font-semibold border transition-colors ${
      active ? activeClass : 'bg-white text-slate-700 border-slate-300 hover:border-slate-400'
    }`}
  >
    {children}
  </button>
);

export const ExpressServiceToggle = ({ quoteData, setQuoteData, expressService }) => {
  const active = !!quoteData.servicio_express;
  const set = (v) => setQuoteData({ ...quoteData, servicio_express: v });
  return (
    <div className="flex-shrink-0 border-l border-slate-200 pl-4" data-testid="express-service-block">
      <label className="text-sm font-semibold text-slate-800 block mb-2">¿Este proyecto requerirá Servicio Express?</label>
      <p className="text-[11px] text-slate-500 mb-2 leading-tight max-w-[220px]">
        Si es Sí, se agrega el concepto "Servicio Express" en el Setup.
      </p>
      <div className="flex gap-1.5" role="radiogroup" aria-label="Servicio Express">
        <OptionButton active={active} onClick={() => set(true)} testId="express-service-yes" activeClass="bg-emerald-600 text-white border-emerald-700 shadow-sm">Sí</OptionButton>
        <OptionButton active={!active} onClick={() => set(false)} testId="express-service-no" activeClass="bg-slate-700 text-white border-slate-800 shadow-sm">No</OptionButton>
      </div>
      {active && !expressService && (
        <p className="text-[11px] text-amber-600 font-semibold mt-1.5 max-w-[220px]" data-testid="express-service-missing">
          No existe "Servicio Express" en el Catálogo de Bienes y Servicios.
        </p>
      )}
    </div>
  );
};
