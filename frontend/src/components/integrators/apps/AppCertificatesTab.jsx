import { useCallback, useEffect, useRef, useState } from 'react';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';
import { Download, RefreshCw, Ban, CheckCircle2, AlertTriangle, Upload, Eye, FolderOpen } from 'lucide-react';
import { CertExpedienteDialog } from './CertExpedienteDialog';
import { CertificateViewer } from './CertificateViewer';
import api from '../../../utils/api';
import { toast } from 'sonner';

const STATUS = {
  vigente: 'bg-emerald-100 text-emerald-700', desactualizado: 'bg-amber-100 text-amber-700',
  reemplazado: 'bg-slate-200 text-slate-600', anulado: 'bg-red-100 text-red-700',
};
const STATUS_LABEL = { vigente: 'Vigente', desactualizado: 'Desactualizado', reemplazado: 'Versión anterior', anulado: 'Anulado' };

const ReissueForm = ({ app, onDone, onCancel }) => {
  const [comp, setComp] = useState(app.cert_component || '');
  const [ver, setVer] = useState(app.cert_version || '');
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    if (!comp.trim() || !ver.trim()) { toast.error('Componente y Versión son obligatorios'); return; }
    setBusy(true);
    try {
      const fd = new FormData(); fd.append('componente', comp.trim()); fd.append('version_componente', ver.trim());
      await api.post(`/integrators/${app.integrator_id}/certificates/reissue`, fd);
      toast.success('Certificado re-emitido con la matriz vigente'); onDone();
    } catch (e) { toast.error(e.response?.data?.detail || 'Error al re-emitir el certificado'); }
    finally { setBusy(false); }
  };
  return (
    <div className="rounded-md border border-blue-200 bg-blue-50/60 p-3 grid grid-cols-5 gap-2 items-end" data-testid="reissue-form">
      <div className="col-span-2"><p className="text-[11px] text-slate-500 mb-1">Componente</p><Input className="h-8 text-sm bg-white" value={comp} onChange={(e) => setComp(e.target.value)} data-testid="reissue-component" /></div>
      <div className="col-span-1"><p className="text-[11px] text-slate-500 mb-1">Versión</p><Input className="h-8 text-sm bg-white" value={ver} onChange={(e) => setVer(e.target.value)} data-testid="reissue-version" /></div>
      <div className="col-span-2 flex gap-1 justify-end">
        <Button size="sm" variant="ghost" onClick={onCancel}>Cancelar</Button>
        <Button size="sm" disabled={busy} onClick={submit} data-testid="reissue-confirm-btn">{busy ? 'Generando...' : 'Emitir certificado'}</Button>
      </div>
    </div>
  );
};

export const AppCertificatesTab = ({ app, canManage, onChanged }) => {
  const [items, setItems] = useState([]);
  const [reissuing, setReissuing] = useState(false);
  const [viewing, setViewing] = useState(null);
  const [expediente, setExpediente] = useState(null);
  const fileRef = useRef(null);
  const uploadPdf = async (e) => {
    const f = e.target.files?.[0]; e.target.value = '';
    if (!f) return;
    if (!/\.pdf$/i.test(f.name)) { toast.error('Solo se permiten archivos PDF'); return; }
    try {
      const fd = new FormData(); fd.append('file', f);
      await api.post(`/integrators/${app.integrator_id}/certificates`, fd, { headers: { 'Content-Type': 'multipart/form-data' } });
      toast.success('Certificado cargado al histórico'); load(); onChanged();
    } catch (err) { toast.error(err.response?.data?.detail || 'Error al cargar el certificado'); }
  };
  const load = useCallback(() => api.get(`/integrators/${app.integrator_id}/certificates`).then((r) => setItems(r.data?.certificates || [])).catch(() => setItems([])), [app.integrator_id]);
  useEffect(() => { load(); }, [load, app]);

  const download = async (c) => {
    try {
      const res = await api.get(`/integrators/certificates/${c.certificate_id}/download`, { responseType: 'blob' });
      const a = document.createElement('a'); a.href = URL.createObjectURL(res.data); a.download = c.original_name || 'certificado.pdf'; a.click();
    } catch { toast.error('No se pudo descargar el certificado'); }
  };
  const setStatus = async (c, status) => {
    try { await api.patch(`/integrators/certificates/${c.certificate_id}/status`, { status }); toast.success(`Certificado marcado como ${status}`); load(); onChanged(); }
    catch (e) { toast.error(e.response?.data?.detail || 'Error al actualizar el certificado'); }
  };

  return (
    <div className="space-y-3" data-testid="app-certs-tab">
      {app.cert_outdated && (
        <div className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-800 flex items-start gap-2" data-testid="cert-outdated-banner">
          <AlertTriangle size={14} className="mt-0.5 shrink-0" />
          <span><b>Certificado desactualizado:</b> la Matriz de Productos cambió después de su emisión{app.cert_outdated_reason ? ` (motivo: ${app.cert_outdated_reason})` : ''}. Debe re-emitirse.</span>
        </div>
      )}
      <div className="flex items-center justify-between">
        <p className="text-[11px] uppercase tracking-wide text-slate-400">Histórico de Certificados ({items.length})</p>
        {canManage && !reissuing && <div className="flex gap-2">
          <input ref={fileRef} type="file" accept=".pdf" className="hidden" onChange={uploadPdf} data-testid="manual-cert-input" />
          <Button size="sm" variant="outline" onClick={() => fileRef.current?.click()} data-testid="manual-cert-btn"><Upload size={13} className="mr-1" />Cargar certificado (PDF)</Button>
          <Button size="sm" variant="outline" onClick={() => setReissuing(true)} data-testid="reissue-cert-btn"><RefreshCw size={13} className="mr-1" />Re-emitir certificado</Button>
        </div>}
      </div>
      {reissuing && <ReissueForm app={app} onCancel={() => setReissuing(false)} onDone={() => { setReissuing(false); load(); onChanged(); }} />}
      {items.length === 0 ? <p className="text-xs text-slate-400">Este aplicativo no tiene certificados emitidos.</p> : (
        <table className="w-full text-xs border border-slate-200 rounded-md overflow-hidden">
          <thead className="bg-slate-100 text-slate-500 text-[11px] uppercase"><tr>
            <th className="text-left px-3 py-2">Versión</th><th className="text-left px-3 py-2">Fecha</th><th className="text-left px-3 py-2">Productos incluidos</th><th className="text-left px-3 py-2">Origen</th>
            <th className="text-left px-3 py-2">Estado</th><th className="px-3 py-2" /></tr></thead>
          <tbody>
            {items.map((c, idx) => (
              <tr key={c.certificate_id} className="border-t border-slate-100 align-top" data-testid={`cert-row-${c.certificate_id}`}>
                <td className="px-3 py-2 whitespace-nowrap font-semibold text-slate-700">Cert. #{String(items.length - idx).padStart(3, '0')}</td>
                <td className="px-3 py-2 whitespace-nowrap">{new Date(c.created_at).toLocaleString('es-VE')}</td>
                <td className="px-3 py-2" data-testid={`cert-products-${c.certificate_id}`}>
                  {c.products_included?.length ? <ul className="list-disc pl-4 space-y-0.5">{c.products_included.map((n) => <li key={n}>{n}</li>)}</ul>
                    : <span className="text-slate-400 break-all" title={c.original_name}>{c.origin === 'manual' ? 'Carga manual (PDF)' : 'Emisión previa al histórico por producto'}</span>}
                </td>
                <td className="px-3 py-2">{c.origin_label}<div className="text-[10px] text-slate-400">{c.created_by_name}</div></td>
                <td className="px-3 py-2"><span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${STATUS[c.status] || STATUS.vigente}`} data-testid={`cert-status-${c.certificate_id}`}>{STATUS_LABEL[c.status] || 'Vigente'}</span>
                  {c.status_note && <div className="text-[10px] text-slate-400 mt-0.5">{c.status_note}</div>}</td>
                <td className="px-3 py-2 text-right whitespace-nowrap">
                  <button className="p-1 text-slate-400 hover:text-brand-blue-600" title="Ver certificado" onClick={() => setViewing(c)} data-testid={`cert-view-${c.certificate_id}`}><Eye size={13} /></button>
                  <button className="p-1 text-slate-400 hover:text-brand-blue-600" title="Descargar" onClick={() => download(c)} data-testid={`cert-download-${c.certificate_id}`}><Download size={13} /></button>
                  <button className="p-1 text-amber-500 hover:text-amber-600 inline-flex items-center gap-0.5" title="Expediente Digital de Certificación"
                    onClick={() => setExpediente({ c, label: `Cert. #${String(items.length - idx).padStart(3, '0')}` })} data-testid={`cert-expediente-${c.certificate_id}`}>
                    <FolderOpen size={13} />{c.expediente_count > 0 && <span className="text-[10px] font-semibold">({c.expediente_count})</span>}
                  </button>
                  {canManage && c.status !== 'vigente' && <button className="p-1 text-slate-400 hover:text-emerald-600" title="Marcar vigente" onClick={() => setStatus(c, 'vigente')} data-testid={`cert-set-vigente-${c.certificate_id}`}><CheckCircle2 size={13} /></button>}
                  {canManage && c.status !== 'anulado' && <button className="p-1 text-slate-400 hover:text-red-600" title="Anular" onClick={() => setStatus(c, 'anulado')} data-testid={`cert-set-anulado-${c.certificate_id}`}><Ban size={13} /></button>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <CertExpedienteDialog cert={expediente?.c} label={expediente?.label} canUpload={canManage}
        onClose={() => setExpediente(null)} onChanged={load} />
      <CertificateViewer cert={viewing} onClose={() => setViewing(null)} onDownload={download} />
    </div>
  );
};
