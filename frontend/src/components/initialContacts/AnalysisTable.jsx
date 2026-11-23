import { Fragment, useState } from 'react';
import { ChevronRight, ChevronDown } from 'lucide-react';
import { formatDate } from '../../utils/dateFormat';

const STATUS_STYLE = { converted: 'bg-emerald-100 text-emerald-700', closed: 'bg-blue-100 text-blue-700', active: 'bg-amber-100 text-amber-700' };
const SEDE = { PYME: 'Pyme', CORP: 'Corporativo' };
const fmtDt = (v) => (v ? new Date(v).toLocaleString('es-VE', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—');

const Interactions = ({ items }) => (
  items.length === 0 ? <p className="text-xs text-slate-400 italic px-4 py-3">Sin interacciones registradas.</p> : (
    <table className="w-full text-xs">
      <thead className="!static text-slate-500 uppercase text-[10px]"><tr>
        <th className="px-3 py-1.5 text-left w-36">Fecha</th><th className="px-3 py-1.5 text-left w-32">Tipo</th><th className="px-3 py-1.5 text-left">Detalle</th>
        <th className="px-3 py-1.5 text-left w-36">Persona Contactada</th><th className="px-3 py-1.5 text-left w-24">Próximo</th><th className="px-3 py-1.5 text-left w-36">Usuario</th>
      </tr></thead>
      <tbody className="divide-y divide-slate-100">
        {items.map((x, i) => (
          <tr key={i}>
            <td className="px-3 py-1.5 text-slate-500 whitespace-nowrap">{fmtDt(x.fecha)}</td>
            <td className="px-3 py-1.5 font-medium text-slate-700">{x.tipo}</td>
            <td className="px-3 py-1.5 text-slate-700 whitespace-pre-wrap">{x.detalle}</td>
            <td className="px-3 py-1.5 text-slate-600">{x.persona_contactada || '—'}</td>
            <td className="px-3 py-1.5 text-slate-600">{x.proximo_contacto ? formatDate(x.proximo_contacto) : '—'}</td>
            <td className="px-3 py-1.5 text-slate-600">{x.usuario}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
);

export const AnalysisTable = ({ items }) => {
  const [open, setOpen] = useState({});
  if (!items.length) return <p className="p-8 text-center text-sm text-slate-400" data-testid="analysis-empty">No hay contactos con los filtros seleccionados</p>;
  return (
    <table className="w-full text-sm" data-testid="analysis-table">
      <thead className="bg-slate-50 text-[11px] uppercase text-slate-500 sticky top-0 z-[1]"><tr>
        <th className="w-8" /><th className="px-3 py-2.5 text-left">Registro</th><th className="px-3 py-2.5 text-left">Contacto</th><th className="px-3 py-2.5 text-left">Razón Social</th>
        <th className="px-3 py-2.5 text-left">Referido Por</th><th className="px-3 py-2.5 text-left">Asignado a</th><th className="px-3 py-2.5 text-left">Segmento</th>
        <th className="px-3 py-2.5 text-left">Estatus</th><th className="px-3 py-2.5 text-center">Interac.</th>
      </tr></thead>
      <tbody className="divide-y divide-slate-100">
        {items.map((c) => (
          <Fragment key={c.contact_id}>
            <tr className="hover:bg-slate-50 cursor-pointer" onClick={() => setOpen((o) => ({ ...o, [c.contact_id]: !o[c.contact_id] }))} data-testid={`analysis-row-${c.contact_id}`}>
              <td className="pl-3 text-slate-400">{open[c.contact_id] ? <ChevronDown size={15} /> : <ChevronRight size={15} />}</td>
              <td className="px-3 py-2 text-slate-500 whitespace-nowrap">{formatDate(c.created_at)}</td>
              <td className="px-3 py-2 font-medium text-slate-800">{c.contact_name}</td>
              <td className="px-3 py-2 text-slate-600">{c.legal_name || '—'}</td>
              <td className="px-3 py-2 text-slate-600">{c.referido_por || '—'}</td>
              <td className="px-3 py-2 text-slate-600">{c.asignado || '—'}</td>
              <td className="px-3 py-2 text-slate-600">{SEDE[c.sede] || c.sede || '—'}</td>
              <td className="px-3 py-2"><span className={`text-[11px] font-semibold px-2 py-0.5 rounded ${STATUS_STYLE[c.status]}`}>{c.status_label}</span></td>
              <td className="px-3 py-2 text-center text-slate-700">{c.interacciones.length}</td>
            </tr>
            {open[c.contact_id] && (
              <tr data-testid={`analysis-interactions-${c.contact_id}`}><td colSpan={9} className="bg-slate-50/70 px-6 py-2">
                {c.closed_reason && <p className="text-xs text-slate-600 mb-1"><b>Motivo de cierre:</b> {c.closed_reason}</p>}
                {c.interest_notes && <p className="text-xs text-slate-600 mb-1"><b>Interés:</b> {c.interest_notes}</p>}
                <div className="bg-white border border-slate-200 rounded-md"><Interactions items={c.interacciones} /></div>
              </td></tr>
            )}
          </Fragment>
        ))}
      </tbody>
    </table>
  );
};
