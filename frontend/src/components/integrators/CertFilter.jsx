import { Award } from 'lucide-react';

const OPTIONS = [['all', 'Todos'], ['with', 'Con Certificado'], ['without', 'Sin Certificado']];

export const certMatches = (value, hasCert) => value === 'all' || (value === 'with' ? hasCert : !hasCert);

export const CertFilter = ({ value, onChange, testId = 'cert-filter' }) => (
  <div className="inline-flex items-center h-9 rounded-md border border-slate-200 bg-white p-0.5 text-xs" role="radiogroup" data-testid={testId}>
    <Award size={13} className="mx-1.5 text-slate-400" />
    {OPTIONS.map(([k, label]) => (
      <button key={k} type="button" role="radio" aria-checked={value === k} onClick={() => onChange(k)} data-testid={`${testId}-${k}`}
        className={`h-full px-2.5 rounded font-medium transition-colors ${value === k ? (k === 'without' ? 'bg-slate-700 text-white' : k === 'with' ? 'bg-green-600 text-white' : 'bg-slate-100 text-slate-800') : 'text-slate-500 hover:text-slate-800'}`}>
        {label}
      </button>
    ))}
  </div>
);
