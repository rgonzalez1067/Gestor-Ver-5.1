const PRE_PROD = 'bg-orange-100 text-orange-800 border-orange-300';
const PROD = 'bg-emerald-100 text-emerald-800 border-emerald-300';

export const PhaseTag = ({ status, testId, className = '' }) => {
  if (!status) return null;
  const tone = status === 'Producción' ? PROD : PRE_PROD;
  return (
    <span
      data-testid={testId}
      className={`inline-flex items-center px-1.5 py-0.5 rounded border text-[10px] font-bold whitespace-nowrap shrink-0 ${tone} ${className}`}
    >
      {status}
    </span>
  );
};
