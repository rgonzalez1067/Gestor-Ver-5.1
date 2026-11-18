import { useState, useRef } from 'react';
import { toast } from 'sonner';
import api from '../../../utils/api';
import { Button } from '../../ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '../../ui/dialog';
import { FileSpreadsheet, Upload, Download, CheckCircle2, AlertCircle, RefreshCw, PlusCircle } from 'lucide-react';

export const downloadBranchTemplate = async (principal) => {
  try {
    const res = await api.get(`/clients/${principal.client_id}/branches/import-template`, { responseType: 'blob' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(res.data);
    a.download = `Plantilla_Sucursales_${(principal.rif || 'RIF').replace(/[^A-Za-z0-9]+/g, '_')}.xlsx`;
    a.click();
    URL.revokeObjectURL(a.href);
  } catch {
    toast.error('No se pudo descargar la plantilla');
  }
};

const ActionTag = ({ r }) => r.errors.length ? (
  <span className="inline-flex items-center gap-1 text-red-600"><AlertCircle size={12} /> Error</span>
) : r.action === 'update' ? (
  <span className="inline-flex items-center gap-1 text-blue-600"><RefreshCw size={12} /> Actualiza</span>
) : (
  <span className="inline-flex items-center gap-1 text-emerald-600"><PlusCircle size={12} /> Nueva</span>
);

const PreviewTable = ({ rows }) => (
  <div className="border rounded-lg max-h-80 overflow-auto">
    <table className="w-full text-xs">
      <thead className="bg-slate-50 sticky top-0 text-slate-600 uppercase">
        <tr><th className="px-2 py-1.5 text-left">Fila</th><th className="px-2 py-1.5 text-left">Sucursal</th><th className="px-2 py-1.5 text-left">Dirección</th>
          <th className="px-2 py-1.5 text-center">Cajas</th><th className="px-2 py-1.5 text-left">Contacto</th><th className="px-2 py-1.5 text-left">Resultado</th></tr>
      </thead>
      <tbody className="divide-y">
        {rows.map(r => (
          <tr key={r.row} className={r.errors.length ? 'bg-red-50/60' : ''} data-testid={`branch-import-row-${r.row}`}>
            <td className="px-2 py-1.5 text-slate-500">{r.row}</td>
            <td className="px-2 py-1.5 font-medium">{r.sucursal || '—'}</td>
            <td className="px-2 py-1.5 text-slate-600 max-w-[220px] truncate" title={r.branch_address}>{r.branch_address || '—'}</td>
            <td className="px-2 py-1.5 text-center">{r.cantidad_cajas ?? '—'}</td>
            <td className="px-2 py-1.5 text-slate-600">{r.contact ? `${r.contact.full_name} · ${r.contact.email || r.contact.phone}` : <span className="text-sky-600">Heredado RIF</span>}</td>
            <td className="px-2 py-1.5"><ActionTag r={r} />{r.errors.length > 0 && <p className="text-[11px] text-red-600">{r.errors.join(' · ')}</p>}</td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);

// Carga masiva de sucursales: subir Excel → vista previa → confirmar.
export const ImportBranchesDialog = ({ open, onOpenChange, principal, onDone }) => {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState(false);
  const inputRef = useRef(null);
  const reset = () => { setFile(null); setPreview(null); if (inputRef.current) inputRef.current.value = ''; };
  const send = async (confirm) => {
    const fd = new FormData();
    fd.append('file', file);
    setBusy(true);
    try {
      const { data } = await api.post(`/clients/${principal.client_id}/branches/import?confirm=${confirm}`, fd, { headers: { 'Content-Type': 'multipart/form-data' } });
      if (!confirm) return setPreview(data);
      toast.success(`Sucursales: ${data.created} creadas, ${data.updated} actualizadas${data.skipped ? `, ${data.skipped} omitidas por error` : ''}`);
      (data.failed || []).forEach(f => toast.error(`Fila ${f.row} (${f.sucursal}): ${f.error}`));
      reset();
      onOpenChange(false);
      onDone?.();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Error al procesar el archivo');
    } finally {
      setBusy(false);
    }
  };
  const s = preview?.summary;

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) reset(); onOpenChange(o); }}>
      <DialogContent className="max-w-4xl" data-testid="branch-import-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><FileSpreadsheet size={18} className="text-emerald-600" /> Importar Sucursales desde Excel
            <span className="text-sm font-normal text-slate-500">· {principal?.rif} — {principal?.legal_name}</span></DialogTitle>
        </DialogHeader>
        <div className="flex flex-wrap items-center gap-3 rounded-lg border border-dashed border-slate-300 p-3 bg-slate-50">
          <Button type="button" variant="outline" size="sm" onClick={() => downloadBranchTemplate(principal)} data-testid="branch-import-template-btn"><Download size={14} className="mr-1" /> Descargar plantilla</Button>
          <input ref={inputRef} type="file" accept=".xlsx" onChange={(e) => { setFile(e.target.files?.[0] || null); setPreview(null); }} className="text-sm" data-testid="branch-import-file" />
          <Button type="button" size="sm" disabled={!file || busy} onClick={() => send(false)} data-testid="branch-import-preview-btn"><Upload size={14} className="mr-1" /> {busy && !preview ? 'Analizando…' : 'Vista previa'}</Button>
        </div>
        {s && (
          <div className="space-y-2">
            <div className="flex flex-wrap gap-2 text-xs" data-testid="branch-import-summary">
              <span className="px-2 py-1 rounded bg-slate-100">{s.total} filas</span>
              <span className="px-2 py-1 rounded bg-emerald-50 text-emerald-700">{s.create} nuevas</span>
              <span className="px-2 py-1 rounded bg-blue-50 text-blue-700">{s.update} a actualizar</span>
              <span className={`px-2 py-1 rounded ${s.errors ? 'bg-red-50 text-red-700' : 'bg-slate-100 text-slate-500'}`}>{s.errors} con error (se omitirán)</span>
            </div>
            <PreviewTable rows={preview.rows} />
          </div>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} data-testid="branch-import-cancel">Cancelar</Button>
          <Button disabled={!s || !s.valid || busy} onClick={() => send(true)} className="bg-emerald-600 hover:bg-emerald-700" data-testid="branch-import-confirm-btn">
            <CheckCircle2 size={14} className="mr-1" /> {busy && preview ? 'Cargando…' : `Confirmar carga${s ? ` (${s.valid})` : ''}`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
