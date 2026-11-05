import { Eye } from 'lucide-react';
import { ACTION_STYLES, fmtDate } from './auditUtils';

const COLS = ['Fecha/Hora', 'Módulo', 'Registro ID', 'Acción', 'Usuario', 'IP Origen', 'Campos', 'Detalle'];

export const AuditTable = ({ items, loading, onView }) => (
  <div className="bg-white border rounded-xl overflow-x-auto" data-testid="audit-table">
    <table className="w-full text-sm">
      <thead className="bg-slate-50 text-slate-600 text-xs uppercase tracking-wide">
        <tr>{COLS.map((c) => <th key={c} className="px-3 py-2.5 text-left font-semibold">{c}</th>)}</tr>
      </thead>
      <tbody>
        {loading && <tr><td colSpan={COLS.length} className="px-3 py-10 text-center text-slate-400">Cargando…</td></tr>}
        {!loading && items.length === 0 && (
          <tr><td colSpan={COLS.length} className="px-3 py-10 text-center text-slate-400" data-testid="audit-empty">Sin pistas para los filtros aplicados.</td></tr>
        )}
        {!loading && items.map((t) => (
          <tr key={t.id} className="border-t hover:bg-slate-50 transition-colors" data-testid={`audit-row-${t.id}`}>
            <td className="px-3 py-2 whitespace-nowrap text-slate-600">{fmtDate(t.fecha_hora)}</td>
            <td className="px-3 py-2 whitespace-nowrap">{t.modulo}</td>
            <td className="px-3 py-2 font-mono text-xs max-w-[220px] truncate" title={t.registro_id}>{t.registro_id}</td>
            <td className="px-3 py-2"><span className={`px-2 py-0.5 rounded text-[11px] font-bold ${ACTION_STYLES[t.accion]}`}>{t.accion}</span></td>
            <td className="px-3 py-2 whitespace-nowrap" title={t.usuario_email}>{t.usuario_nombre}</td>
            <td className="px-3 py-2 font-mono text-xs">{t.ip_origen || '—'}</td>
            <td className="px-3 py-2 text-xs text-slate-500 max-w-[240px] truncate" title={(t.campos_modificados || []).join(', ')}>
              {t.accion === 'UPDATE' ? (t.campos_modificados || []).join(', ') : '—'}
            </td>
            <td className="px-3 py-2">
              <button type="button" onClick={() => onView(t.id)} className="inline-flex items-center gap-1 text-xs font-semibold text-[#003366] hover:underline" data-testid={`audit-view-btn-${t.id}`}>
                <Eye size={14} />Ver
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);
