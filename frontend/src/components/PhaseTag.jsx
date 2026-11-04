const PRE_PROD = 'bg-orange-100 text-orange-800 border-orange-300';

export const PhaseTag = ({ status, testId, className = '' }) => {
  if (!status || status === 'Producción') return null;
  const tone = PRE_PROD;
  return (
    <span
      data-testid={testId}
      className={`inline-flex items-center px-1.5 py-0.5 rounded border text-[10px] font-bold whitespace-nowrap shrink-0 ${tone} ${className}`}
    >
      {status}
    </span>
  );
};
