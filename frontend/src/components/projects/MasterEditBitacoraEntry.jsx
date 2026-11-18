import { MessageSquareQuote, PencilRuler } from 'lucide-react';

const fmt = (v) => (v === null || v === undefined || v === '' ? '—' : String(v));

// Entrada de bitácora de Edición Maestra: justificación resaltada + detalle de campos.
export const MasterEditBitacoraEntry = ({ entry }) => {
  const changes = entry.changes || [];
  const justification = entry.justification || '';
  const header = (entry.text || '').split(' | Justificación:')[0].split(': ')[0];
  return (
    <div className="space-y-2" data-testid={`master-edit-entry-${entry.entry_id}`}>
      <p className="text-sm font-semibold text-slate-800 flex items-center gap-1.5"><PencilRuler size={14} className="text-slate-500" />{header}</p>
      {justification && (
        <div className="flex items-start gap-2 rounded-md border-l-4 border-amber-500 bg-amber-50 px-3 py-2" data-testid={`master-edit-justification-${entry.entry_id}`}>
          <MessageSquareQuote size={15} className="text-amber-600 shrink-0 mt-0.5" />
          <div>
            <p className="text-[10px] font-bold uppercase tracking-wide text-amber-700">Justificación</p>
            <p className="text-sm text-amber-900 whitespace-pre-line">{justification}</p>
          </div>
        </div>
      )}
      {changes.length > 0 && (
        <div className="rounded-md border border-slate-200 overflow-hidden" data-testid={`master-edit-changes-${entry.entry_id}`}>
          <table className="w-full text-xs">
            <thead className="bg-slate-50 text-slate-500"><tr><th className="px-2 py-1 text-left">Campo</th><th className="px-2 py-1 text-left">Anterior</th><th className="px-2 py-1 text-left">Nuevo</th></tr></thead>
            <tbody className="divide-y">
              {changes.map((c, i) => (
                <tr key={i}><td className="px-2 py-1 font-medium text-slate-700">{c.label}</td>
                  <td className="px-2 py-1 text-red-600 line-through decoration-red-300">{fmt(c.old)}</td>
                  <td className="px-2 py-1 text-emerald-700">{fmt(c.new)}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
