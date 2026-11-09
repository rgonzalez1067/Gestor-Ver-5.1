import { GitBranch } from 'lucide-react';
import { LevelTag } from './levels';

// rows: [{field,label,value,source_level,overridden}] desde /inheritance
export const InheritanceSummary = ({ rows = [], testId = 'inheritance-summary' }) => {
  if (!rows.length) return null;
  return (
    <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg" data-testid={testId}>
      <div className="flex items-center gap-2 mb-2">
        <GitBranch size={14} className="text-indigo-600" />
        <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-600">Herencia de características</h4>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1.5">
        {rows.map(r => (
          <div key={r.field} className="flex flex-wrap items-center gap-x-1.5 gap-y-0.5 text-xs min-w-0" data-testid={`inheritance-row-${r.field}`}>
            <span className="text-slate-500 shrink-0">{r.label}:</span>
            <span className="font-medium text-slate-800 break-words min-w-0">{r.value || '—'}</span>
            {r.source_level && r.value ? <LevelTag scope={r.source_level} testId={`inheritance-source-${r.field}`} /> : null}
          </div>
        ))}
      </div>
    </div>
  );
};
