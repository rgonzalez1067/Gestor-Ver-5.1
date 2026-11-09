export const LEVELS = {
  grupo: { label: 'Grupo Económico', tag: 'bg-purple-100 text-purple-800 border-purple-200' },
  marca: { label: 'Marca', tag: 'bg-teal-100 text-teal-800 border-teal-200' },
  principal: { label: 'RIF / Razón Social', tag: 'bg-indigo-100 text-indigo-800 border-indigo-200' },
  local: { label: 'Sucursal', tag: 'bg-amber-100 text-amber-800 border-amber-200' },
};

export const LEVEL_ORDER = ['grupo', 'marca', 'principal', 'local'];

export const LevelTag = ({ scope, testId }) => {
  const lv = LEVELS[scope] || LEVELS.principal;
  return (
    <span data-testid={testId} className={`inline-flex items-center px-1.5 py-0.5 rounded border text-[10px] font-semibold whitespace-nowrap ${lv.tag}`}>
      [{lv.label}]
    </span>
  );
};
