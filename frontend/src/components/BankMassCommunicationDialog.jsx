import { useState, useEffect, useMemo } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './ui/dialog';
import { Button } from './ui/button';
import { Label } from './ui/label';
import { Checkbox } from './ui/checkbox';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Send, Landmark, Search, Paperclip, Users, FileText, Eye, Download } from 'lucide-react';
import { toast } from 'sonner';
import api from '../utils/api';
import { DocumentViewerModal, downloadEntityDocument } from './DocumentViewerModal';

const checkState = (keys, selected) => {
  const n = keys.filter(k => selected.has(k)).length;
  return n === 0 ? false : n === keys.length ? true : 'indeterminate';
};

const BankGroup = ({ bank, selected, onToggleBank, onToggleOne }) => {
  const keys = bank.contacts.filter(c => c.has_email).map(c => c.key);
  const n = keys.filter(k => selected.has(k)).length;
  return (
    <tbody data-testid={`bank-group-${bank.bank_id}`}>
      <tr className="bg-slate-100/80 border-t border-slate-200">
        <td className="p-2 w-10">
          <Checkbox checked={checkState(keys, selected)} disabled={keys.length === 0}
            onCheckedChange={() => onToggleBank(keys)} data-testid={`bank-check-${bank.bank_id}`} />
        </td>
        <td colSpan={3} className="p-2 font-semibold text-slate-800">
          <span className="flex items-center gap-2"><Landmark size={14} className="text-emerald-600" />{bank.name}
            <span className="text-[11px] font-normal text-slate-500">{n}/{keys.length} seleccionado(s)</span></span>
        </td>
      </tr>
      {bank.contacts.map(c => (
        <tr key={c.key} className={`border-t border-slate-100 ${!c.has_email ? 'opacity-50' : 'hover:bg-emerald-50/40'}`} data-testid={`bank-contact-row-${c.key}`}>
          <td className="p-2 pl-6"><Checkbox disabled={!c.has_email} checked={selected.has(c.key)}
            onCheckedChange={() => onToggleOne(c.key)} data-testid={`bank-contact-check-${c.key}`} /></td>
          <td className="p-2 text-slate-700">{c.name || '—'}</td>
          <td className="p-2 text-slate-500 font-mono text-xs">{c.email || <span className="italic text-rose-400">sin correo</span>}</td>
          <td className="p-2 text-slate-600 text-xs">{c.position || '—'}</td>
        </tr>
      ))}
    </tbody>
  );
};

export const BankMassCommunicationDialog = ({ open, onOpenChange }) => {
  const [banks, setBanks] = useState([]);
  const [selected, setSelected] = useState(new Set());
  const [search, setSearch] = useState('');
  const [templates, setTemplates] = useState([]);
  const [templateId, setTemplateId] = useState('');
  const [previewOpen, setPreviewOpen] = useState(false);
  const [docs, setDocs] = useState([]);
  const [selectedDocs, setSelectedDocs] = useState(new Set());
  const [localFiles, setLocalFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [viewerDoc, setViewerDoc] = useState(null);

  useEffect(() => {
    if (!open) return;
    setSelected(new Set()); setTemplateId(''); setSelectedDocs(new Set()); setLocalFiles([]); setSearch('');
    setLoading(true);
    api.get('/banks/mass/recipients').then(r => setBanks(r.data?.banks || [])).catch(() => setBanks([])).finally(() => setLoading(false));
    api.get('/email-templates?context=INTEGRADORES').then(r => setTemplates(r.data || [])).catch(() => setTemplates([]));
    api.get('/entity-documents?context=INTEGRADORES').then(r => setDocs(r.data || [])).catch(() => setDocs([]));
  }, [open]);

  const visible = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return banks;
    return banks.map(b => b.name.toLowerCase().includes(q) ? b : {
      ...b, contacts: b.contacts.filter(c => [c.name, c.email, c.position].some(v => (v || '').toLowerCase().includes(q))),
    }).filter(b => b.contacts.length > 0);
  }, [banks, search]);

  const allKeys = useMemo(() => visible.flatMap(b => b.contacts.filter(c => c.has_email).map(c => c.key)), [visible]);
  const hiddenSelected = useMemo(() => {
    const vis = new Set(allKeys);
    return Array.from(selected).filter(k => !vis.has(k)).length;
  }, [selected, allKeys]);
  const totalWithEmail = banks.reduce((a, b) => a + b.contacts.filter(c => c.has_email).length, 0);
  const tpl = templates.find(t => t.template_id === templateId);
  const sendMode = useMemo(() => {
    const txt = `${tpl?.subject || ''} ${tpl?.body_html || ''} ${tpl?.body || ''}`;
    if (/\{\{?contacto_(nombre|cargo|email|telefono)\}?\}/.test(txt)) return 'per_contact';
    if (/\{\{?banco_(nombre|rif|codigo|tipo|pais|procesador)\}?\}/.test(txt)) return 'per_bank';
    return 'single';
  }, [tpl]);
  const selectedBanks = useMemo(() => new Set(Array.from(selected).map(k => k.split('::')[0])).size, [selected]);

  const toggleKeys = (keys) => {
    const next = new Set(selected);
    const allOn = keys.every(k => next.has(k));
    keys.forEach(k => (allOn ? next.delete(k) : next.add(k)));
    setSelected(next);
  };
  const toggleOne = (k) => { const next = new Set(selected); next.has(k) ? next.delete(k) : next.add(k); setSelected(next); };
  const toggleDoc = (id) => { const next = new Set(selectedDocs); next.has(id) ? next.delete(id) : next.add(id); setSelectedDocs(next); };

  const handleSend = async () => {
    if (!templateId) { toast.error('Seleccione una plantilla'); return; }
    if (selected.size === 0) { toast.error('Seleccione al menos un contacto con correo'); return; }
    setSending(true);
    try {
      const fd = new FormData();
      fd.append('template_id', templateId);
      fd.append('contact_keys', JSON.stringify(Array.from(selected)));
      fd.append('internal_doc_ids', JSON.stringify(Array.from(selectedDocs)));
      localFiles.forEach(f => fd.append('files', f));
      const res = await api.post('/banks/mass/communication', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
      toast.success(res.data?.message || 'Comunicación masiva enviada');
      onOpenChange(false);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Error al enviar la comunicación masiva');
    } finally { setSending(false); }
  };

  return (
    <>
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-6xl max-h-[92vh] overflow-hidden flex flex-col" data-testid="bank-mass-comm-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-emerald-700"><Landmark size={20} />Comunicación Masiva a Bancos/Entes</DialogTitle>
          <DialogDescription className="text-xs text-slate-500">Seleccione contactos, plantilla y adjuntos. El envío se realiza en copia oculta (BCC).</DialogDescription>
        </DialogHeader>
        <div className="flex-1 overflow-y-auto grid grid-cols-1 lg:grid-cols-5 gap-5 pr-1">
          <div className="lg:col-span-3 flex flex-col min-h-0">
            <div className="relative mb-2">
              <Search size={14} className="absolute left-2.5 top-2.5 text-slate-400" />
              <input value={search} onChange={e => setSearch(e.target.value)} placeholder="Buscar banco, contacto, correo o cargo…"
                className="w-full pl-8 pr-3 py-2 text-sm border border-slate-200 rounded-lg" data-testid="bank-mass-search" />
            </div>
            <div className="text-xs text-slate-500 mb-1 flex items-center gap-1.5" data-testid="bank-mass-counter">
              <Users size={12} /> {selected.size} seleccionado(s) · {totalWithEmail} con correo en {banks.length} Banco(s)/Ente(s)
            </div>
            {hiddenSelected > 0 && (
              <div className="text-xs mb-1 px-2 py-1 rounded bg-amber-50 border border-amber-200 text-amber-800 flex items-center justify-between" data-testid="bank-mass-hidden-warning">
                <span>{hiddenSelected} contacto(s) seleccionado(s) ocultos por la búsqueda también recibirán el correo.</span>
                <button type="button" className="underline ml-2" data-testid="bank-mass-clear-hidden"
                  onClick={() => setSelected(new Set(Array.from(selected).filter(k => allKeys.includes(k))))}>Quitar ocultos</button>
              </div>
            )}
            <div className="border border-slate-200 rounded-lg overflow-auto" style={{ maxHeight: '50vh' }}>
              <table className="w-full text-sm">
                <thead className="bg-slate-50 sticky top-0 z-10">
                  <tr className="text-left text-xs text-slate-500">
                    <th className="p-2 w-10"><Checkbox checked={checkState(allKeys, selected)} disabled={allKeys.length === 0}
                      onCheckedChange={() => toggleKeys(allKeys)} data-testid="bank-mass-select-all" /></th>
                    <th className="p-2">Nombre</th><th className="p-2">Correo Electrónico</th><th className="p-2">Cargo</th>
                  </tr>
                </thead>
                {loading ? (
                  <tbody><tr><td colSpan={4} className="p-6 text-center text-slate-400">Cargando…</td></tr></tbody>
                ) : visible.length === 0 ? (
                  <tbody><tr><td colSpan={4} className="p-6 text-center text-slate-400">Sin contactos</td></tr></tbody>
                ) : visible.map(b => (
                  <BankGroup key={b.bank_id} bank={b} selected={selected} onToggleBank={toggleKeys} onToggleOne={toggleOne} />
                ))}
              </table>
            </div>
          </div>
          <div className="lg:col-span-2 space-y-4">
            <div>
              <Label className="text-sm font-medium">Plantilla (biblioteca de Integradores)</Label>
              <div className="flex gap-2 mt-1">
                <Select value={templateId} onValueChange={setTemplateId}>
                  <SelectTrigger data-testid="bank-mass-template-select"><SelectValue placeholder="Seleccione una plantilla…" /></SelectTrigger>
                  <SelectContent>
                    {templates.map(t => <SelectItem key={t.template_id} value={t.template_id} data-testid={`bank-mass-tpl-${t.template_id}`}>{t.name}</SelectItem>)}
                  </SelectContent>
                </Select>
                <Button variant="outline" size="icon" disabled={!tpl} onClick={() => setPreviewOpen(true)} title="Vista previa" data-testid="bank-mass-template-preview-btn"><Eye size={16} /></Button>
              </div>
              {templates.length === 0 && <p className="text-xs text-slate-400 mt-1">No hay plantillas en la biblioteca de Integradores.</p>}
              {tpl && (
                <p className="text-[11px] mt-1.5 px-2 py-1 rounded bg-slate-50 border border-slate-200 text-slate-600" data-testid="bank-mass-send-mode">
                  Modo de envío: <strong>{sendMode === 'per_contact' ? `un correo individual por contacto (${selected.size})`
                    : sendMode === 'per_bank' ? `un correo por Banco/Ente en BCC (${selectedBanks})`
                    : 'un solo correo en BCC'}</strong>
                </p>
              )}
            </div>
            <div>
              <Label className="text-sm font-medium flex items-center gap-1"><FileText size={14} />Documentos del repositorio</Label>
              <div className="mt-1 border border-slate-200 rounded-lg p-2 space-y-1 max-h-32 overflow-auto">
                {docs.length === 0 ? <p className="text-xs text-slate-400">Repositorio vacío</p> : docs.map(d => (
                  <div key={d.document_id} className="flex items-center gap-1 text-xs hover:bg-slate-50 p-1 rounded" data-testid={`bank-mass-doc-${d.document_id}`}>
                    <label className="flex items-center gap-2 flex-1 min-w-0 cursor-pointer">
                      <Checkbox checked={selectedDocs.has(d.document_id)} onCheckedChange={() => toggleDoc(d.document_id)} />
                      <span className="truncate">{d.filename}</span>
                    </label>
                    <button type="button" onClick={() => setViewerDoc(d)} className="p-1 text-slate-400 hover:text-blue-600" title="Visualizar" data-testid={`bank-mass-doc-view-${d.document_id}`}><Eye size={14} /></button>
                    <button type="button" onClick={() => downloadEntityDocument(d)} className="p-1 text-slate-400 hover:text-emerald-600" title="Descargar" data-testid={`bank-mass-doc-download-${d.document_id}`}><Download size={14} /></button>
                  </div>
                ))}
              </div>
            </div>
            <div>
              <Label className="text-sm font-medium flex items-center gap-1"><Paperclip size={14} />Anexo local adicional</Label>
              <input type="file" multiple onChange={e => setLocalFiles(Array.from(e.target.files || []))}
                className="mt-1 block w-full text-xs text-slate-600 file:mr-3 file:py-2 file:px-3 file:rounded-lg file:border-0 file:bg-emerald-600 file:text-white file:cursor-pointer hover:file:bg-emerald-700" data-testid="bank-mass-local-files" />
              {localFiles.length > 0 && <p className="text-xs text-slate-500 mt-1">{localFiles.length} archivo(s) local(es)</p>}
            </div>
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-2.5 text-xs text-amber-800">
              Privacidad: todos los correos se envían en <strong>copia oculta (BCC)</strong>. Solo los contactos marcados reciben la comunicación.
            </div>
          </div>
        </div>
        <div className="flex items-center justify-between gap-3 pt-3 border-t mt-1">
          <span className="text-xs text-slate-500">{selected.size} destinatario(s) · {selectedDocs.size + localFiles.length} adjunto(s)</span>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => onOpenChange(false)} data-testid="bank-mass-cancel">Cancelar</Button>
            <Button onClick={handleSend} disabled={sending || selected.size === 0 || !templateId}
              className="bg-emerald-600 hover:bg-emerald-700 text-white" data-testid="bank-mass-send-btn">
              <Send size={14} className="mr-1.5" />{sending ? 'Enviando…' : `Enviar a ${selected.size}`}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
    <Dialog open={previewOpen} onOpenChange={setPreviewOpen}>
      <DialogContent className="max-w-3xl max-h-[85vh] overflow-auto" data-testid="bank-mass-template-preview">
        <DialogHeader><DialogTitle className="text-sm">{tpl?.subject || tpl?.name}</DialogTitle></DialogHeader>
        <div className="border rounded-lg p-3 bg-white text-sm [&_h1]:text-xl [&_h1]:font-bold [&_h2]:text-lg [&_h2]:font-semibold [&_h3]:font-semibold [&_p]:my-2 [&_ul]:list-disc [&_ul]:pl-5 [&_ol]:list-decimal [&_ol]:pl-5 [&_a]:text-blue-600 [&_a]:underline" dangerouslySetInnerHTML={{ __html: tpl?.body_html || tpl?.body || '' }} />
      </DialogContent>
    </Dialog>
    <DocumentViewerModal open={!!viewerDoc} onOpenChange={(v) => !v && setViewerDoc(null)} doc={viewerDoc} />
    </>
  );
};

export default BankMassCommunicationDialog;
