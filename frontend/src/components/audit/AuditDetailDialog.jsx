import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../ui/dialog';
import { ACTION_STYLES, fmtDate } from './auditUtils';

const fmtVal = (v) => {
  if (v === null || v === undefined) return '—';
  if (typeof v === 'object') return JSON.stringify(v, null, 2);
  return String(v);
};

const DiffRows = ({ trail }) => {
  const prev = trail.valores_anteriores || {};
  const next = trail.valores_nuevos || {};
  const keys = trail.accion === 'UPDATE'
    ? (trail.campos_modificados || [])
    : Object.keys(trail.accion === 'CREATE' ? next : prev).sort();
  if (!keys.length) return <p className="text-sm text-slate-500">Sin campos.</p>;
  return (
    <div className="border rounded-lg overflow-hidden" data-testid="audit-diff-table">
      <div className="grid grid-cols-[minmax(160px,1fr)_2fr_2fr] bg-slate-100 text-xs font-semibold text-slate-600">
        <div className="px-3 py-2">Campo</div>
        <div className="px-3 py-2">Valor anterior</div>
        <div className="px-3 py-2">Valor nuevo</div>
      </div>
      {keys.map((k) => (
        <div key={k} className="grid grid-cols-[minmax(160px,1fr)_2fr_2fr] border-t text-xs" data-testid={`audit-diff-row-${k}`}>
          <div className="px-3 py-2 font-mono text-slate-700 break-all">{k}</div>
          <pre className="px-3 py-2 bg-red-50 text-red-700 whitespace-pre-wrap break-all font-mono max-h-48 overflow-auto">{trail.accion === 'CREATE' ? '—' : fmtVal(prev[k])}</pre>
          <pre className="px-3 py-2 bg-emerald-50 text-emerald-700 whitespace-pre-wrap break-all font-mono max-h-48 overflow-auto">{trail.accion === 'DELETE' ? '—' : fmtVal(next[k])}</pre>
        </div>
      ))}
    </div>
  );
};

const Meta = ({ label, value, testid }) => (
  <div>
    <p className="text-[11px] uppercase tracking-wide text-slate-400">{label}</p>
    <p className="text-sm text-slate-800 break-all" data-testid={testid}>{value || '—'}</p>
  </div>
);

export const AuditDetailDialog = ({ trail, onClose }) => (
  <Dialog open={!!trail} onOpenChange={(o) => !o && onClose()}>
    <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto" data-testid="audit-detail-dialog">
      {trail && (
        <>
          <DialogHeader>
            <DialogTitle className="flex items-center gap-3">
              <span className={`px-2 py-0.5 rounded text-xs font-bold ${ACTION_STYLES[trail.accion]}`}>{trail.accion}</span>
              {trail.modulo} · {trail.registro_id}
            </DialogTitle>
            <DialogDescription>Registro inmutable de solo lectura.</DialogDescription>
          </DialogHeader>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 bg-slate-50 rounded-lg p-4 mb-4">
            <Meta label="Fecha/Hora" value={fmtDate(trail.fecha_hora)} testid="audit-meta-date" />
            <Meta label="Usuario" value={`${trail.usuario_nombre || ''} ${trail.usuario_email ? `(${trail.usuario_email})` : ''}`} testid="audit-meta-user" />
            <Meta label="IP Origen" value={trail.ip_origen} testid="audit-meta-ip" />
            <Meta label="Entidad" value={`${trail.entidad} · ${trail.entidad_id}`} testid="audit-meta-entity" />
            <div className="col-span-2"><Meta label="Endpoint / Función" value={trail.endpoint} testid="audit-meta-endpoint" /></div>
            <div className="col-span-2"><Meta label="User-Agent" value={trail.user_agent} testid="audit-meta-ua" /></div>
          </div>
          <DiffRows trail={trail} />
        </>
      )}
    </DialogContent>
  </Dialog>
);
