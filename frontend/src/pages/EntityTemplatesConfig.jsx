import { useState, useEffect, useRef } from 'react';
import { Sidebar } from '../components/Sidebar';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '../components/ui/dialog';
import { ArrowLeft, FileText, Upload, Trash2, Plus, Save, Pencil, FileUp, Eye, Download, Mail, FileStack } from 'lucide-react';
import { RichTextEditor } from '../components/RichTextEditor';
import { FusionHeaderZone, FusionFooterZone, FusionCoverOptions } from '../components/templates/FusionZones';
import { DocumentViewerModal, downloadEntityDocument } from '../components/DocumentViewerModal';
import api from '../utils/api';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';
import { usePermission } from '../hooks/usePermission';

/**
 * Gestor genérico de plantillas + documentos por contexto.
 * Props (via useParams o wrappers):
 *   context, title, subtitle, backPath, permissionKey, templateIdPrefix, variablesHint
 */
export const EntityTemplatesConfig = ({
  context,
  title,
  subtitle,
  backPath = '/dashboard',
  backLabel = 'Volver',
  permissionKey,
  templateIdPrefix = 'tpl',
  variablesHint = '',
  variableGroups = null,
  allowFusion = false,
}) => {
  const navigate = useNavigate();
  const editorRef = useRef(null);
  const subjectFocusRef = useRef(false);
  const headerRef = useRef(null);
  const footerRef = useRef(null);
  const zoneRef = useRef('body');
  const { user: currentUser } = usePermission(permissionKey);
  const isAdmin = currentUser?.role === 'admin';

  const [activeTab, setActiveTab] = useState('plantillas');
  const [templates, setTemplates] = useState([]);
  const [tplDialogOpen, setTplDialogOpen] = useState(false);
  const [editingTpl, setEditingTpl] = useState(null);
  const EMPTY_FUSION = { header_html: '', footer_html: '', portada_encabezado: true, portada_pie: true };
  const [tplForm, setTplForm] = useState({ name: '', subject: '', body_html: '', tipo_plantilla: 'COMUNICACION', ...EMPTY_FUSION });
  const [typePickerOpen, setTypePickerOpen] = useState(false);
  const isFusion = tplForm.tipo_plantilla === 'FUSION';

  const [documents, setDocuments] = useState([]);
  const [docDialogOpen, setDocDialogOpen] = useState(false);
  const [docForm, setDocForm] = useState({ name: '', description: '', category: 'General' });
  const [docFile, setDocFile] = useState(null);
  const fileRef = useRef(null);
  const [viewerDoc, setViewerDoc] = useState(null);
  const [viewerOpen, setViewerOpen] = useState(false);

  const fetchTemplates = () => api.get(`/email-templates?context=${context}`).then(r => setTemplates(r.data || [])).catch(() => {});
  const fetchDocuments = () => api.get(`/entity-documents?context=${context}`).then(r => setDocuments(r.data || [])).catch(() => {});

  useEffect(() => { fetchTemplates(); fetchDocuments(); /* eslint-disable-next-line */ }, [context]);

  const startNewTemplate = (tipo) => {
    setTypePickerOpen(false);
    setEditingTpl(null);
    zoneRef.current = 'body';
    setTplForm({ name: '', subject: '', body_html: '', tipo_plantilla: tipo, ...EMPTY_FUSION });
    setTplDialogOpen(true);
  };
  const openNewTemplate = () => (allowFusion ? setTypePickerOpen(true) : startNewTemplate('COMUNICACION'));
  const openEditTemplate = (tpl) => {
    setEditingTpl(tpl);
    zoneRef.current = 'body';
    setTplForm({ name: tpl.name, subject: tpl.subject || '', body_html: tpl.body_html || tpl.body || '', tipo_plantilla: tpl.tipo_plantilla || 'COMUNICACION',
      header_html: tpl.header_html || '', footer_html: tpl.footer_html || '', portada_encabezado: tpl.portada_encabezado !== false, portada_pie: tpl.portada_pie !== false });
    setTplDialogOpen(true);
  };
  const saveTemplate = async () => {
    if (!tplForm.name.trim()) { toast.error(isFusion ? 'El título es obligatorio' : 'El nombre es obligatorio'); return; }
    if (isFusion && !tplForm.body_html.replace(/<[^>]+>|&nbsp;|\s/g, '')) { toast.error('El cuerpo del documento es obligatorio'); return; }
    if (allowFusion && !isFusion && !tplForm.subject.trim()) { toast.error('El asunto es obligatorio para plantillas de comunicación'); return; }
    const payload = isFusion ? { ...tplForm, subject: null } : { name: tplForm.name, subject: tplForm.subject, body_html: tplForm.body_html, tipo_plantilla: tplForm.tipo_plantilla };
    try {
      if (editingTpl) {
        await api.put(`/email-templates/${editingTpl.template_id}`, {
          template_id: editingTpl.template_id,
          ...payload, context, is_active: true,
        });
        toast.success('Plantilla actualizada');
      } else {
        const newId = `${templateIdPrefix}_${Date.now().toString(36)}`;
        await api.post('/email-templates', {
          template_id: newId, ...payload, context, is_active: true,
        });
        toast.success('Plantilla creada');
      }
      setTplDialogOpen(false);
      fetchTemplates();
    } catch (err) { toast.error(err.response?.data?.detail || 'Error al guardar'); }
  };
  const deleteTemplate = async (tpl) => {
    if (!window.confirm(`¿Eliminar plantilla "${tpl.name}"?`)) return;
    try {
      await api.delete(`/email-templates/${tpl.template_id}`);
      toast.success('Plantilla eliminada');
      fetchTemplates();
    } catch { toast.error('Error al eliminar'); }
  };

  const uploadDocument = async () => {
    if (!docForm.name.trim()) { toast.error('El nombre es obligatorio'); return; }
    if (!docFile) { toast.error('Seleccione un archivo'); return; }
    try {
      const formData = new FormData();
      formData.append('context', context);
      formData.append('name', docForm.name);
      formData.append('description', docForm.description);
      formData.append('category', docForm.category);
      formData.append('file', docFile);
      await api.post('/entity-documents/upload', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
      toast.success('Documento subido');
      setDocDialogOpen(false);
      setDocFile(null);
      setDocForm({ name: '', description: '', category: 'General' });
      fetchDocuments();
    } catch (err) { toast.error(err.response?.data?.detail || 'Error al subir'); }
  };
  const deleteDocument = async (doc) => {
    if (!window.confirm(`¿Eliminar "${doc.name}"?`)) return;
    try {
      await api.delete(`/entity-documents/${doc.document_id}`);
      toast.success('Documento eliminado');
      fetchDocuments();
    } catch { toast.error('Error al eliminar'); }
  };

  return (
    <div className="flex min-h-screen bg-slate-50">
      <Sidebar />
      <main className="flex-1 p-6 overflow-auto">
        <div className="flex items-center gap-3 mb-6">
          <Button variant="ghost" size="sm" onClick={() => navigate(backPath)} data-testid="entity-tpl-back">
            <ArrowLeft className="w-4 h-4 mr-1" /> {backLabel}
          </Button>
          <div>
            <h1 className="text-xl font-bold text-slate-800">{title}</h1>
            {subtitle && <p className="text-sm text-slate-500">{subtitle}</p>}
          </div>
        </div>

        <div className="flex gap-2 mb-6">
          <Button variant={activeTab === 'plantillas' ? 'default' : 'outline'} size="sm"
            onClick={() => setActiveTab('plantillas')} data-testid="entity-tab-plantillas">
            <FileText className="w-4 h-4 mr-1" /> {allowFusion ? 'Plantillas' : 'Plantillas de Correo'}
          </Button>
          <Button variant={activeTab === 'documentos' ? 'default' : 'outline'} size="sm"
            onClick={() => setActiveTab('documentos')} data-testid="entity-tab-documentos">
            <FileUp className="w-4 h-4 mr-1" /> Documentos de Comunicación
          </Button>
        </div>

        {activeTab === 'plantillas' && (
          <div>
            <div className="flex justify-between items-center mb-4">
              {variablesHint && <p className="text-xs text-slate-500">Variables disponibles: <code className="text-blue-600">{variablesHint}</code></p>}
              <Button size="sm" onClick={openNewTemplate} data-testid="entity-new-template-btn">
                <Plus className="w-4 h-4 mr-1" /> Nueva Plantilla
              </Button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {templates.map(tpl => (
                <div key={tpl.template_id} className="bg-white rounded-lg border border-slate-200 p-4 hover:border-blue-300 transition" data-testid={`entity-tpl-card-${tpl.template_id}`}>
                  <div className="flex justify-between items-start mb-2">
                    <h4 className="font-semibold text-sm text-slate-800">{tpl.name}</h4>
                    <div className="flex gap-1">
                      <Button variant="ghost" size="sm" onClick={() => openEditTemplate(tpl)} className="h-7 w-7 p-0">
                        <Pencil className="w-3.5 h-3.5 text-slate-400" />
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => deleteTemplate(tpl)} className="h-7 w-7 p-0">
                        <Trash2 className="w-3.5 h-3.5 text-slate-400 hover:text-rose-500" />
                      </Button>
                    </div>
                  </div>
                  {allowFusion && (tpl.tipo_plantilla === 'FUSION'
                    ? <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 border border-amber-200 mb-1.5" data-testid={`tpl-badge-fusion-${tpl.template_id}`}><FileStack className="w-3 h-3" />Plantilla de Fusión</span>
                    : <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 border border-blue-200 mb-1.5" data-testid={`tpl-badge-comunicacion-${tpl.template_id}`}><Mail className="w-3 h-3" />Comunicación</span>)}
                  {tpl.tipo_plantilla === 'FUSION' && (
                    <p className="text-[10px] text-slate-500 mb-1" data-testid={`tpl-fusion-zones-${tpl.template_id}`}>
                      Encabezado: {(tpl.header_html || '').replace(/<[^>]+>/g, '').trim() || /<img/i.test(tpl.header_html || '') ? 'Sí' : 'No'} · Pie: {(tpl.footer_html || '').replace(/<[^>]+>/g, '').trim() || /<img/i.test(tpl.footer_html || '') ? 'Sí' : 'No'} · Portada: {tpl.portada_encabezado === false && tpl.portada_pie === false ? 'sin encabezado/pie' : `${tpl.portada_encabezado === false ? 'sin' : 'con'} encabezado, ${tpl.portada_pie === false ? 'sin' : 'con'} pie`}
                    </p>
                  )}
                  {tpl.tipo_plantilla !== 'FUSION' && <p className="text-xs text-blue-600 font-medium mb-1">Asunto: {tpl.subject || '—'}</p>}
                  <p className="text-xs text-slate-500 line-clamp-3">{(tpl.body_html || tpl.body || '—').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim() || '—'}</p>
                </div>
              ))}
              {templates.length === 0 && (
                <div className="col-span-full text-center py-12 text-slate-400">
                  <FileText className="w-10 h-10 mx-auto mb-2 opacity-40" />
                  <p>No hay plantillas. Cree la primera.</p>
                </div>
              )}
            </div>

            <Dialog open={tplDialogOpen} onOpenChange={setTplDialogOpen}>
              <DialogContent className="max-w-3xl max-h-[90vh] flex flex-col p-0 overflow-hidden" data-testid="entity-template-dialog">
                <DialogHeader className="px-6 pt-6 pb-3 shrink-0 border-b border-slate-100">
                  <DialogTitle className="flex items-center gap-2 flex-wrap">{editingTpl ? 'Editar' : 'Nueva'} {isFusion ? 'Plantilla de Fusión' : 'Plantilla'}
                    {allowFusion && <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full border ${isFusion ? 'bg-amber-100 text-amber-800 border-amber-200' : 'bg-blue-100 text-blue-700 border-blue-200'}`} data-testid="entity-tpl-type-badge">{isFusion ? 'Plantilla de Fusión' : 'Comunicación'}</span>}
                  </DialogTitle>
                  <DialogDescription>{isFusion ? 'Plantilla documental para ensamblaje y generación de documentos de certificación. No se envía por correo.' : 'Estas plantillas son específicas del módulo y no interfieren con otros.'}</DialogDescription>
                </DialogHeader>
                <div className="space-y-3 flex-1 min-h-0 overflow-y-auto px-6 py-4" data-testid="entity-template-body">
                  <div><Label className="text-xs">{isFusion ? <>Título Identificativo <span className="text-red-500">*</span></> : <>Nombre</>}</Label><Input value={tplForm.name} maxLength={isFusion ? 150 : undefined} onChange={e => setTplForm({...tplForm, name: e.target.value})} data-testid="entity-tpl-name" /></div>
                  {!isFusion && <div><Label className="text-xs">Asunto{allowFusion && <span className="text-red-500"> *</span>}</Label><Input value={tplForm.subject}
                    onFocus={() => { subjectFocusRef.current = true; }}
                    onChange={e => setTplForm({...tplForm, subject: e.target.value})} data-testid="entity-tpl-subject" /></div>}
                  {variableGroups && (
                    <div className="border border-slate-200 rounded-lg p-2.5 bg-slate-50 space-y-2" data-testid="entity-tpl-variables">
                      <p className="text-[11px] text-slate-500">{isFusion ? 'Clic en una variable para insertarla en la zona editada por última vez (Encabezado, Cuerpo o Pie de Página).' : 'Clic en una variable para insertarla en el cuerpo (o en el asunto si es el último campo editado).'}</p>
                      {variableGroups.map(g => (
                        <div key={g.title}>
                          <p className="text-[11px] font-semibold text-slate-600 mb-1">{g.title}{g.note && <span className="font-normal text-slate-400"> — {g.note}</span>}</p>
                          <div className="flex flex-wrap gap-1">
                            {g.vars.map(v => (
                              <button key={v.key} type="button" title={v.label}
                                className={`text-[11px] px-2 py-0.5 rounded border font-mono transition-colors ${g.tone || 'bg-white border-blue-200 text-blue-700 hover:bg-blue-50'}`}
                                onMouseDown={(e) => e.preventDefault()}
                                onClick={() => {
                                  const token = `{{${v.key}}}`;
                                  if (subjectFocusRef.current && !isFusion) setTplForm(f => ({ ...f, subject: `${f.subject}${token}` }));
                                  else if (isFusion && zoneRef.current === 'header') headerRef.current?.insertText(token);
                                  else if (isFusion && zoneRef.current === 'footer') footerRef.current?.insertText(token);
                                  else editorRef.current?.insertText(token);
                                }}
                                data-testid={`entity-tpl-var-${v.key}`}>
                                {`{{${v.key}}}`}
                              </button>
                            ))}
                          </div>
                        </div>
                      ))}
                      {isFusion && (
                        <div>
                          <p className="text-[11px] font-semibold text-slate-600 mb-1">Paginación <span className="font-normal text-slate-400">— opcional, se resuelve al generar el documento</span></p>
                          <div className="flex flex-wrap gap-1">
                            {[{ key: 'pagina', label: 'Número de página actual' }, { key: 'total_paginas', label: 'Total de páginas' }].map(v => (
                              <button key={v.key} type="button" title={v.label} onMouseDown={(e) => e.preventDefault()}
                                onClick={() => { const t = `{{${v.key}}}`; (zoneRef.current === 'header' ? headerRef : zoneRef.current === 'footer' ? footerRef : editorRef).current?.insertText(t); }}
                                className="text-[11px] px-2 py-0.5 rounded border font-mono transition-colors bg-white border-amber-200 text-amber-700 hover:bg-amber-50"
                                data-testid={`entity-tpl-var-${v.key}`}>{`{{${v.key}}}`}</button>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                  {isFusion && <FusionCoverOptions form={tplForm} setForm={setTplForm} />}
                  {isFusion && <FusionHeaderZone form={tplForm} setForm={setTplForm} editorRef={headerRef} zoneRef={zoneRef} context={context} />}
                  <div>
                    <Label className="text-xs">{isFusion ? <>Cuerpo / Estructura del Documento <span className="text-red-500">*</span></> : 'Cuerpo del Mensaje'}</Label>
                    <div onMouseDown={() => { subjectFocusRef.current = false; zoneRef.current = 'body'; }}>
                    <RichTextEditor
                      ref={editorRef}
                      value={tplForm.body_html}
                      onChange={(html) => { subjectFocusRef.current = false; zoneRef.current = 'body'; setTplForm(f => ({ ...f, body_html: html })); }}
                      maxChars={20000}
                      hardLimit={false}
                      placeholder={isFusion ? 'Redacte aquí la estructura del documento...' : 'Redacte aquí el cuerpo del correo...'}
                      testid={`entity-tpl-editor-${context}`} enableFontSize={isFusion}
                      showPreview
                      minHeight={240}
                      maxHeight={400}
                    />
                    </div>
                    {variablesHint && !variableGroups && <p className="text-[10px] text-slate-400 mt-1">Variables: {variablesHint}</p>}
                  </div>
                  {isFusion && <FusionFooterZone form={tplForm} setForm={setTplForm} editorRef={footerRef} zoneRef={zoneRef} context={context} />}
                </div>
                <DialogFooter className="px-6 py-4 border-t border-slate-100 bg-white shrink-0">
                  <Button variant="outline" onClick={() => setTplDialogOpen(false)}>Cancelar</Button>
                  <Button onClick={saveTemplate} data-testid="entity-template-save-btn"><Save className="w-4 h-4 mr-1" /> {isFusion ? 'Guardar Plantilla' : 'Guardar'}</Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
            <TemplateTypePicker open={typePickerOpen} onOpenChange={setTypePickerOpen} onPick={startNewTemplate} />
          </div>
        )}

        {activeTab === 'documentos' && (
          <div>
            <div className="flex justify-end mb-4">
              <Button size="sm" onClick={() => { setDocForm({ name: '', description: '', category: 'General' }); setDocFile(null); setDocDialogOpen(true); }} data-testid="entity-upload-doc-btn">
                <Upload className="w-4 h-4 mr-1" /> Subir Documento
              </Button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {documents.map(doc => (
                <div key={doc.document_id} className="bg-white rounded-lg border border-slate-200 p-4 flex items-center gap-3" data-testid={`entity-doc-${doc.document_id}`}>
                  <div className="p-2.5 bg-slate-100 rounded-lg"><FileText className="w-5 h-5 text-blue-600" /></div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-slate-800 truncate">{doc.name}</p>
                    <p className="text-[10px] text-slate-400 truncate">{doc.filename} | {doc.category}</p>
                  </div>
                  <Button variant="ghost" size="sm" onClick={() => { setViewerDoc(doc); setViewerOpen(true); }} className="h-8 w-8 p-0 text-slate-400 hover:text-blue-600 shrink-0" title="Visualizar documento" data-testid={`entity-doc-view-${doc.document_id}`}>
                    <Eye className="w-4 h-4" />
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => downloadEntityDocument(doc)} className="h-8 w-8 p-0 text-slate-400 hover:text-emerald-600 shrink-0" title="Descargar documento" data-testid={`entity-doc-download-${doc.document_id}`}>
                    <Download className="w-4 h-4" />
                  </Button>
                  {isAdmin && (
                    <Button variant="ghost" size="sm" onClick={() => deleteDocument(doc)} className="h-8 w-8 p-0 text-slate-300 hover:text-rose-500 shrink-0" title="Eliminar documento">
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  )}
                </div>
              ))}              {documents.length === 0 && (
                <div className="col-span-full text-center py-12 text-slate-400">
                  <FileUp className="w-10 h-10 mx-auto mb-2 opacity-40" />
                  <p>No hay documentos cargados.</p>
                </div>
              )}
            </div>

            <Dialog open={docDialogOpen} onOpenChange={setDocDialogOpen}>
              <DialogContent className="max-w-md" data-testid="entity-upload-doc-dialog">
                <DialogHeader>
                  <DialogTitle>Subir Documento</DialogTitle>
                  <DialogDescription>Disponible como adjunto al enviar comunicaciones.</DialogDescription>
                </DialogHeader>
                <div className="space-y-3 min-w-0">
                  <div className="min-w-0"><Label className="text-xs">Nombre</Label><Input value={docForm.name} onChange={e => setDocForm({...docForm, name: e.target.value})} /></div>
                  <div className="min-w-0"><Label className="text-xs">Descripción (opcional)</Label><Input value={docForm.description} onChange={e => setDocForm({...docForm, description: e.target.value})} /></div>
                  <div className="min-w-0">
                    <Label className="text-xs">Archivo</Label>
                    <div className="mt-1">
                      <Button variant="outline" size="sm" onClick={() => fileRef.current?.click()} className="w-full justify-start max-w-full" title={docFile ? docFile.name : undefined}>
                        <Upload className="w-3.5 h-3.5 mr-1 shrink-0" /> <span className="truncate min-w-0">{docFile ? docFile.name : 'Seleccionar archivo'}</span>
                      </Button>
                      <input type="file" ref={fileRef} onChange={e => setDocFile(e.target.files?.[0] || null)} className="hidden" />
                    </div>
                  </div>
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setDocDialogOpen(false)}>Cancelar</Button>
                  <Button onClick={uploadDocument}><Upload className="w-4 h-4 mr-1" /> Subir</Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        )}
      </main>
      <DocumentViewerModal open={viewerOpen} onOpenChange={setViewerOpen} doc={viewerDoc} />
    </div>
  );
};

const TemplateTypePicker = ({ open, onOpenChange, onPick }) => (
  <Dialog open={open} onOpenChange={onOpenChange}>
    <DialogContent className="max-w-lg" data-testid="tpl-type-picker">
      <DialogHeader>
        <DialogTitle>Nueva Plantilla</DialogTitle>
        <DialogDescription>Seleccione el tipo de plantilla a crear.</DialogDescription>
      </DialogHeader>
      <div className="grid grid-cols-2 gap-3">
        <button type="button" onClick={() => onPick('COMUNICACION')} data-testid="tpl-type-comunicacion"
          className="text-left p-4 rounded-lg border border-slate-200 hover:border-blue-400 hover:bg-blue-50 transition-colors">
          <Mail className="w-5 h-5 text-blue-600 mb-2" />
          <p className="text-sm font-semibold text-slate-800">Comunicación</p>
          <p className="text-[11px] text-slate-500 mt-1">Envío de correos y notificaciones. Requiere Asunto.</p>
        </button>
        <button type="button" onClick={() => onPick('FUSION')} data-testid="tpl-type-fusion"
          className="text-left p-4 rounded-lg border border-slate-200 hover:border-amber-400 hover:bg-amber-50 transition-colors">
          <FileStack className="w-5 h-5 text-amber-600 mb-2" />
          <p className="text-sm font-semibold text-slate-800">Plantilla de Fusión</p>
          <p className="text-[11px] text-slate-500 mt-1">Ensamblaje de documentos técnicos/legales de certificación. Sin Asunto.</p>
        </button>
      </div>
    </DialogContent>
  </Dialog>
);

// Wrappers específicos por módulo
const INTEGRATOR_VARIABLE_GROUPS = [
  { title: 'Integradores', vars: [
    { key: 'nombre_integrador', label: 'Nombre del Integrador' }, { key: 'razon_social', label: 'Razón Social' },
    { key: 'rif', label: 'RIF' }, { key: 'email', label: 'Correo' }, { key: 'telefono', label: 'Teléfono' },
    { key: 'contacto', label: 'Contacto' }, { key: 'estado', label: 'Estatus' },
    { key: 'aplicativo', label: 'Aplicativo' }, { key: 'fase', label: 'Fase' },
  ] },
  { title: 'Empresa Integradora y Certificación', tone: 'bg-white border-violet-200 text-violet-700 hover:bg-violet-50', vars: [
    { key: 'empresa_integradora', label: 'Empresa Integradora (Razón Social)' }, { key: 'rif_integrador', label: 'RIF de la Empresa Integradora' },
    { key: 'direccion_fiscal', label: 'Dirección Fiscal' }, { key: 'contactos_integrador', label: 'Contactos de la Empresa Integradora' },
    { key: 'nombre_aplicativo', label: 'Nombre del Aplicativo' }, { key: 'tipo_integracion', label: 'Tipo de Integración' },
    { key: 'productos_certificados', label: 'Productos certificados (lineal)' }, { key: 'productos_a_certificar', label: 'Productos a certificar (S Nuevo / R Recertificación)' }, { key: 'medios_pago_certificados', label: 'Medios de Pago certificados (lineal)' },
    { key: 'fecha_actual', label: 'Fecha actual (dd/mm/aaaa)' },
  ] },
  { title: 'Bancos y Entes', note: 'un correo por Banco/Ente (BCC)', tone: 'bg-white border-emerald-200 text-emerald-700 hover:bg-emerald-50', vars: [
    { key: 'banco_nombre', label: 'Nombre del Banco/Ente' }, { key: 'banco_razon_social', label: 'Nombre Jurídico' }, { key: 'banco_rif', label: 'RIF del Banco/Ente' },
    { key: 'banco_codigo', label: 'Código bancario' }, { key: 'banco_tipo', label: 'Tipo (Banco/Ente)' },
    { key: 'banco_pais', label: 'País' }, { key: 'banco_procesador', label: 'Procesador' },
  ] },
  { title: 'Contacto del Banco/Ente', note: 'un correo individual por contacto', tone: 'bg-white border-amber-200 text-amber-700 hover:bg-amber-50', vars: [
    { key: 'contacto_nombre', label: 'Nombre del contacto' }, { key: 'contacto_cargo', label: 'Cargo' },
    { key: 'contacto_email', label: 'Correo del contacto' }, { key: 'contacto_telefono', label: 'Teléfono del contacto' },
  ] },
  { title: 'Generales', tone: 'bg-white border-slate-200 text-slate-600 hover:bg-slate-100', vars: [
    { key: 'fecha_sistema', label: 'Fecha del sistema' }, { key: 'Firma_Notificacion_Global', label: 'Firma del usuario' },
  ] },
];
export const IntegratorTemplatesConfig = () => (
  <EntityTemplatesConfig
    context="INTEGRADORES"
    title="Comunicaciones a Integradores"
    subtitle="Plantillas y documentos para notificar integradores/aplicativos"
    backPath="/integrators"
    backLabel="Integradores"
    permissionKey="integradores"
    templateIdPrefix="int_tpl"
    variablesHint="{{nombre_integrador}}, {{razon_social}}, {{rif}}, {{email}}, {{telefono}}, {{contacto}}, {{estado}}, {{aplicativo}}, {{fase}} · Bancos/Entes: {{banco_nombre}}, {{banco_rif}}, {{banco_codigo}}, {{banco_tipo}}, {{banco_pais}}, {{banco_procesador}}, {{contacto_nombre}}, {{contacto_cargo}}, {{contacto_email}}, {{contacto_telefono}}"
    variableGroups={INTEGRATOR_VARIABLE_GROUPS}
    allowFusion
  />
);

export const NewProductTemplatesConfig = () => (
  <EntityTemplatesConfig
    context="NUEVOS_PRODUCTOS"
    title="Comunicaciones de Nuevos Productos"
    subtitle="Plantillas y documentos para comunicaciones de I+D"
    backPath="/new-products"
    backLabel="Nuevos Productos"
    permissionKey="nuevos_productos"
    templateIdPrefix="np_tpl"
    variablesHint="{{producto}}, {{categoria}}, {{estado}}, {{desarrollador}}, {{sqa}}, {{fecha_entrega}}, {{banco}}"
  />
);

export default EntityTemplatesConfig;
