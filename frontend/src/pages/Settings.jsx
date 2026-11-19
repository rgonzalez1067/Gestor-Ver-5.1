import { useState, useEffect, useRef } from 'react';
import { formatDateTime, formatDate, formatTime } from '../utils/dateFormat';
import { Sidebar } from '../components/Sidebar';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Upload, Trash2, Image, FileText, Check, X, Download, Mail, Save, Building2, Warehouse, FileCode, Key, Eye, EyeOff, CheckCircle, AlertCircle, MapPin, TrendingUp, RefreshCw, Clock, Settings2, ChevronRight, ShieldCheck, ChevronDown, Wifi, DatabaseBackup, PenLine, CalendarDays, Bell, Gauge, Inbox, ScrollText } from 'lucide-react';
import { Badge } from '../components/ui/badge';
import api from '../utils/api';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';
import { usePermission } from '../hooks/usePermission';

// Sedes disponibles
const SEDES = [
  { id: 'PYME', name: 'PYME', shortName: 'PYME' },
  { id: 'CORP', name: 'CORP', shortName: 'CORP' }
];

const TEMPLATE_TYPES = [
  { id: 'vpos_pyme', name: 'VPOS Pyme', description: 'Cotización para pequeñas y medianas empresas con VPOS' },
  { id: 'vpos_corporativo', name: 'VPOS Corporativo', description: 'Cotización para empresas corporativas con VPOS' },
  { id: 'payment_gateway', name: 'Payment Gateway', description: 'Cotización para pasarela de pagos (Ecommerce)' },
  { id: 'mpos', name: 'MPOS', description: 'Cotización para soluciones móviles (Tablet/Android)' },
  { id: 'dispositivos', name: 'Dispositivos', description: 'Cotización de dispositivos de pago' },
  { id: 'accesorios', name: 'Accesorios', description: 'Cotización de accesorios complementarios' }
];

export const Settings = () => {
  const { canEdit } = usePermission('configuracion');
  const navigate = useNavigate();
  const [logoUrl, setLogoUrl] = useState(null);
  const [generalConfigOpen, setGeneralConfigOpen] = useState(false);
  const [notifLogoUrl, setNotifLogoUrl] = useState(null);
  const [appendingSignature, setAppendingSignature] = useState(false);
  const [notifUploading, setNotifUploading] = useState(false);
  const [notifDragOver, setNotifDragOver] = useState(false);  const [loading, setLoading] = useState(true);
  const [backfillRunning, setBackfillRunning] = useState(false);
  // ===== Zona de Peligro (oculta): borrar todas las colecciones excepto Admin =====
  // Se revela con la combinación Ctrl + Shift + Alt + K.
  const [dangerUnlocked, setDangerUnlocked] = useState(false);
  const [wipeModalOpen, setWipeModalOpen] = useState(false);
  const [wipeConfirmText, setWipeConfirmText] = useState('');
  const [wiping, setWiping] = useState(false);

  useEffect(() => {
    const onKey = (e) => {
      if (e.ctrlKey && e.shiftKey && e.altKey && (e.key === 'k' || e.key === 'K')) {
        e.preventDefault();
        // Idempotente: el combo SIEMPRE revela la zona (no alterna) para evitar
        // que un doble keydown la vuelva a ocultar. Además expande la sección
        // "Configuración General" donde vive la tarjeta oculta.
        setDangerUnlocked(true);
        setGeneralConfigOpen(true);
        toast.warning('Zona de peligro desbloqueada');
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const handleWipeAll = async () => {
    if (wipeConfirmText.trim() !== 'BORRAR TODO') return;
    if (!window.confirm('ÚLTIMA ADVERTENCIA: se borrarán TODAS las colecciones excepto el usuario y la clave del Administrador. Esta acción es IRREVERSIBLE. ¿Continuar?')) return;
    setWiping(true);
    try {
      const { data } = await api.post('/admin/danger/wipe-all-except-admin', { confirm: 'BORRAR TODO' });
      toast.success(`Base de datos reiniciada. Colecciones limpiadas: ${data?.deleted?.cleared_collections_count ?? 0}. Admin(s) preservado(s): ${data?.preserved?.admin_users ?? 0}.`);
      setWipeModalOpen(false);
      setWipeConfirmText('');
      setDangerUnlocked(false);
      setTimeout(() => window.location.reload(), 1500);
    } catch (err) {
      toast.error(err?.response?.data?.detail || 'Error al borrar las colecciones');
    } finally {
      setWiping(false);
    }
  };


  const runBitacoraBackfill = async () => {
    if (!window.confirm('¿Rescatar los correos históricos de la Bitácora de Proyectos convirtiéndolos a texto simple legible? El HTML original se conserva; el proceso es seguro y repetible.')) return;
    setBackfillRunning(true);
    try {
      const res = await api.post('/projects/bitacora/backfill-plaintext');
      const d = res.data || {};
      toast.success(`Rescate completado: ${d.entries_converted ?? 0} correo(s) convertido(s) en ${d.projects_updated ?? 0} proyecto(s).`);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Error al ejecutar el rescate');
    } finally {
      setBackfillRunning(false);
    }
  };
  const [uploading, setUploading] = useState(false);
  const [seeding, setSeeding] = useState(false);
  const [templates, setTemplates] = useState({});
  const [uploadingTemplate, setUploadingTemplate] = useState(null);
  
  // Correos por sede
  const [emailsBySede, setEmailsBySede] = useState({
    PYME: { admin: '', warehouse: '', sales: '', operations: '' },
    CORP: { admin: '', warehouse: '', sales: '' }
  });
  const [implementationEmail, setImplementationEmail] = useState('');
  const [implManagerEmail, setImplManagerEmail] = useState('');
  const [savingEmail, setSavingEmail] = useState(false);
  
  // Resend API Key state
  const [resendApiKey, setResendApiKey] = useState('');
  const [resendApiKeyConfigured, setResendApiKeyConfigured] = useState(false);
  const [resendApiKeyMasked, setResendApiKeyMasked] = useState('');
  const [showResendKey, setShowResendKey] = useState(false);
  const [savingResendKey, setSavingResendKey] = useState(false);
  // Collapsible state para secciones de Correos por Sede (PYME / CORP) — inicia colapsado
  const [openSedes, setOpenSedes] = useState({ PYME: false, CORP: false });
  const fileInputRef = useRef(null);
  const templateInputRefs = useRef({});
  const notifLogoInputRef = useRef(null);

  useEffect(() => {
    fetchLogo();
    fetchNotifLogo();
    fetchTemplates();
    fetchSettings();

  }, []);

  const fetchSettings = async () => {
    try {
      const [settingsRes] = await Promise.all([api.get('/config/settings')]);
      const response = settingsRes;
      setImplementationEmail(response.data.implementation_email || '');
      setImplManagerEmail(response.data.implementation_manager_email || '');
      
      // Cargar correos por sede
      setEmailsBySede({
        PYME: {
          admin: response.data.emails_by_sede?.PYME?.admin || response.data.admin_email || '',
          warehouse: response.data.emails_by_sede?.PYME?.warehouse || response.data.warehouse_email || '',
          sales: response.data.emails_by_sede?.PYME?.sales || '',
          operations: response.data.emails_by_sede?.PYME?.operations || response.data.operations_email || ''
        },
        CORP: {
          admin: response.data.emails_by_sede?.CORP?.admin || '',
          warehouse: response.data.emails_by_sede?.CORP?.warehouse || '',
          sales: response.data.emails_by_sede?.CORP?.sales || ''
        }
      });
      
      setResendApiKeyConfigured(response.data.resend_api_key_configured || false);
      setResendApiKeyMasked(response.data.resend_api_key_masked || '');
    } catch (error) {
      console.error('Error fetching settings:', error);
    }
  };

  const handleSaveResendKey = async () => {
    if (!resendApiKey.trim()) {
      toast.error('Por favor ingrese una API Key válida');
      return;
    }
    
    setSavingResendKey(true);
    try {
      await api.put('/config/settings', { 
        implementation_email: implementationEmail || null,
        implementation_manager_email: implManagerEmail || null,
        emails_by_sede: emailsBySede,
        resend_api_key: resendApiKey
      });
      setResendApiKeyConfigured(true);
      setResendApiKeyMasked(`${'*'.repeat(resendApiKey.length - 4)}${resendApiKey.slice(-4)}`);
      setResendApiKey(''); // Limpiar el campo
      setShowResendKey(false);
      toast.success('API Key de Resend configurada correctamente');
    } catch (error) {
      toast.error('Error al guardar la API Key');
    } finally {
      setSavingResendKey(false);
    }
  };

  const handleSaveEmails = async () => {
    setSavingEmail(true);
    try {
      await api.put('/config/settings', { 
        implementation_email: implementationEmail || null,
        implementation_manager_email: implManagerEmail || null,
        emails_by_sede: emailsBySede
      });
      toast.success('Configuración de correos guardada');
    } catch (error) {
      toast.error('Error al guardar la configuración');
    } finally {
      setSavingEmail(false);
    }
  };

  // Actualizar email por sede
  const updateSedeEmail = (sedeId, type, value) => {
    setEmailsBySede(prev => ({
      ...prev,
      [sedeId]: {
        ...prev[sedeId],
        [type]: value
      }
    }));
  };

  const fetchLogo = async () => {
    try {
      const response = await api.get('/config/logo', { responseType: 'blob' });
      const url = URL.createObjectURL(response.data);
      setLogoUrl(url);
    } catch (error) {
      if (error.response?.status !== 404) {
        console.error('Error fetching logo:', error);
      }
    } finally {
      setLoading(false);
    }
  };

  const fetchTemplates = async () => {
    try {
      const response = await api.get('/config/templates');
      setTemplates(response.data);
    } catch (error) {
      console.error('Error fetching templates:', error);
    }
  };

  const handleTemplateUpload = async (templateType, event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (file.type !== 'application/pdf') {
      toast.error('Por favor seleccione un archivo PDF');
      return;
    }

    setUploadingTemplate(templateType);
    const formData = new FormData();
    formData.append('file', file);

    try {
      await api.post(`/config/templates/${templateType}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      toast.success('Plantilla subida exitosamente');
      fetchTemplates();
    } catch (error) {
      console.error('Error uploading template:', error);
      toast.error('Error al subir la plantilla');
    } finally {
      setUploadingTemplate(null);
      // Reset the input
      if (templateInputRefs.current[templateType]) {
        templateInputRefs.current[templateType].value = '';
      }
    }
  };

  const handleTemplateDelete = async (templateType) => {
    if (!window.confirm('¿Está seguro de eliminar esta plantilla?')) return;

    try {
      await api.delete(`/config/templates/${templateType}`);
      toast.success('Plantilla eliminada exitosamente');
      fetchTemplates();
    } catch (error) {
      console.error('Error deleting template:', error);
      toast.error('Error al eliminar la plantilla');
    }
  };

  const handleTemplateDownload = async (templateType, templateName) => {
    try {
      const response = await api.get(`/config/templates/${templateType}`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `plantilla_${templateType}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      toast.success('Plantilla descargada');
    } catch (error) {
      toast.error('Error al descargar la plantilla');
    }
  };

  const handleFileSelect = async (event) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith('image/')) {
      toast.error('Por favor seleccione un archivo de imagen');
      return;
    }

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      await api.post('/config/logo', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      toast.success('Logo subido exitosamente');
      fetchLogo();
    } catch (error) {
      console.error('Error uploading logo:', error);
      toast.error('Error al subir el logo');
    } finally {
      setUploading(false);
    }
  };

  const handleDeleteLogo = async () => {
    if (!window.confirm('¿Está seguro de eliminar el logo?')) return;

    try {
      await api.delete('/config/logo');
      setLogoUrl(null);
      toast.success('Logo eliminado exitosamente');
    } catch (error) {
      console.error('Error deleting logo:', error);
      toast.error('Error al eliminar el logo');
    }
  };

  // ── Logotipo para Pie de Notificaciones (Firma institucional) ──
  const fetchNotifLogo = async () => {
    try {
      const response = await api.get('/config/notification-logo', { responseType: 'blob' });
      setNotifLogoUrl(URL.createObjectURL(response.data));
    } catch (error) {
      if (error.response?.status !== 404) console.error('Error fetching notif logo:', error);
      setNotifLogoUrl(null);
    }
  };

  const uploadNotifLogo = async (file) => {
    if (!file) return;
    if (!file.type.startsWith('image/')) { toast.error('Seleccione una imagen .png o .jpg'); return; }
    setNotifUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    try {
      await api.post('/config/notification-logo', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
      toast.success('Logotipo de notificaciones subido');
      fetchNotifLogo();
    } catch (error) {
      toast.error(`Error: ${error.response?.data?.detail || 'No se pudo subir'}`);
    } finally {
      setNotifUploading(false);
    }
  };

  const handleDeleteNotifLogo = async () => {
    if (!window.confirm('¿Eliminar el logotipo de notificaciones?')) return;
    try {
      await api.delete('/config/notification-logo');
      setNotifLogoUrl(null);
      toast.success('Logotipo de notificaciones eliminado');
    } catch (error) {
      toast.error('Error al eliminar');
    }
  };

  const handleAppendSignatureToTemplates = async () => {
    if (!window.confirm('Se agregará la variable {Firma_Notificacion_Global} al pie de TODAS las plantillas de correo que aún no la tengan. ¿Continuar?')) return;
    setAppendingSignature(true);
    try {
      const res = await api.post('/email-templates/append-signature');
      const { updated = 0, skipped = 0 } = res.data || {};
      toast.success(`Firma agregada a ${updated} plantilla(s). ${skipped} ya la tenían.`);
    } catch (error) {
      toast.error(`Error: ${error.response?.data?.detail || 'No se pudo homologar las plantillas'}`);
    } finally {
      setAppendingSignature(false);
    }
  };

  const handleSeedBanks = async () => {
    if (!window.confirm('¿Desea poblar la base de datos con bancos de Venezuela, EE.UU. y Fintechs?')) return;

    setSeeding(true);
    try {
      const response = await api.post('/banks/seed');
      toast.success(response.data.message);
    } catch (error) {
      console.error('Error seeding banks:', error);
      toast.error('Error al poblar la base de datos');
    } finally {
      setSeeding(false);
    }
  };

  if (loading) {
    return (
      <div className="flex min-h-screen">
        <Sidebar />
        <div className="flex-1 flex items-center justify-center bg-white">
          <div className="text-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-green-600 mx-auto"></div>
            <p className="mt-4 text-slate-900">Cargando configuración...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-white">
      <Sidebar />
      
      <main className="flex-1 p-8" data-testid="settings-page">
        <div className="max-w-4xl mx-auto">
          <div className="mb-8">
            <h1 className="text-4xl font-bold text-slate-900 font-manrope mb-2">
              Configuración
            </h1>
            <p className="text-slate-600">Personalice la aplicación según sus necesidades</p>
          </div>

          {/* Logo Section */}
          <div className="bg-white rounded-lg border border-slate-200 p-6 mb-6">
            <h2 className="text-xl font-semibold text-slate-900 font-manrope mb-4 flex items-center gap-2">
              <Image size={24} />
              Logo de la Empresa
            </h2>
            <p className="text-slate-600 mb-6">
              Suba el logo de su empresa para personalizar las cotizaciones y documentos.
            </p>

            <div className="flex items-start gap-8">
              <div className="flex-shrink-0">
                {logoUrl ? (
                  <div className="relative">
                    <img
                      src={logoUrl}
                      alt="Logo de la empresa"
                      className="w-48 h-48 object-contain border border-slate-200 rounded-lg bg-slate-50 p-2"
                      data-testid="company-logo"
                    />
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={handleDeleteLogo}
                      className="absolute -top-2 -right-2 text-red-600 hover:text-red-700 hover:border-red-300 bg-white"
                      data-testid="delete-logo-button"
                    >
                      <Trash2 size={16} />
                    </Button>
                  </div>
                ) : (
                  <div className="w-48 h-48 border-2 border-dashed border-slate-300 rounded-lg flex flex-col items-center justify-center bg-slate-50">
                    <Image size={48} className="text-slate-400 mb-2" />
                    <p className="text-sm text-slate-500">Sin logo</p>
                  </div>
                )}
              </div>

              <div className="flex-1">
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileSelect}
                  accept="image/*"
                  className="hidden"
                  data-testid="logo-file-input"
                />
                <Button
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploading}
                  className="bg-brand-green-600 hover:bg-brand-green-700 text-white"
                  data-testid="upload-logo-button"
                >
                  <Upload size={20} className="mr-2" />
                  {uploading ? 'Subiendo...' : 'Subir Logo'}
                </Button>
                <p className="text-sm text-slate-500 mt-3">
                  Formatos soportados: PNG, JPG, JPEG, GIF, SVG
                </p>
                <p className="text-sm text-slate-500">
                  Tamaño recomendado: 200x200 píxeles o mayor
                </p>
              </div>
            </div>
          </div>

          {/* Logotipo para Pie de Notificaciones (Firma institucional global) */}
          <div className="bg-white rounded-lg border border-slate-200 p-6 mb-6" data-testid="notification-logo-section">
            <h2 className="text-xl font-semibold text-slate-900 font-manrope mb-1 flex items-center gap-2">
              <Image size={24} className="text-emerald-600" />
              Logotipo para Pie de Notificaciones
            </h2>
            <p className="text-slate-600 mb-4">
              Logo exclusivo para la <strong>firma institucional</strong> de correos y notificaciones.
              Se combina con los datos del usuario en sesión en la variable global{' '}
              <code className="bg-slate-100 px-1.5 py-0.5 rounded text-xs text-emerald-700">{'{Firma_Notificacion_Global}'}</code>,
              disponible en todos los editores de plantillas.
            </p>

            <div className="flex items-start gap-8">
              <div className="flex-shrink-0">
                {notifLogoUrl ? (
                  <div className="relative">
                    <img
                      src={notifLogoUrl}
                      alt="Logotipo de notificaciones"
                      className="w-48 h-32 object-contain border border-slate-200 rounded-lg bg-slate-50 p-2"
                      data-testid="notification-logo-preview"
                    />
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={handleDeleteNotifLogo}
                      className="absolute -top-2 -right-2 text-red-600 hover:text-red-700 hover:border-red-300 bg-white"
                      data-testid="delete-notification-logo-button"
                    >
                      <Trash2 size={16} />
                    </Button>
                  </div>
                ) : (
                  <div className="w-48 h-32 border-2 border-dashed border-slate-300 rounded-lg flex flex-col items-center justify-center bg-slate-50">
                    <Image size={40} className="text-slate-400 mb-2" />
                    <p className="text-sm text-slate-500">Sin logo</p>
                  </div>
                )}
              </div>

              <div className="flex-1">
                <div
                  onDragOver={(e) => { e.preventDefault(); setNotifDragOver(true); }}
                  onDragLeave={() => setNotifDragOver(false)}
                  onDrop={(e) => { e.preventDefault(); setNotifDragOver(false); uploadNotifLogo(e.dataTransfer.files?.[0]); }}
                  onClick={() => notifLogoInputRef.current?.click()}
                  className={`border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors ${notifDragOver ? 'border-emerald-500 bg-emerald-50' : 'border-slate-300 hover:bg-slate-50'}`}
                  data-testid="notification-logo-dropzone"
                >
                  <Upload size={28} className="mx-auto text-emerald-600 mb-2" />
                  <p className="text-sm font-medium text-slate-700">
                    {notifUploading ? 'Subiendo...' : 'Arrastra y suelta el logo aquí, o haz clic para seleccionar'}
                  </p>
                  <p className="text-xs text-slate-500 mt-1">PNG o JPG, con soporte de fondo transparente</p>
                </div>
                <input
                  type="file"
                  ref={notifLogoInputRef}
                  onChange={(e) => uploadNotifLogo(e.target.files?.[0])}
                  accept=".png,.jpg,.jpeg,image/png,image/jpeg"
                  className="hidden"
                  data-testid="notification-logo-file-input"
                />
              </div>
            </div>

            {/* Homologación: insertar la firma global en todas las plantillas */}
            <div className="mt-6 pt-5 border-t border-slate-200 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3" data-testid="append-signature-row">
              <div className="flex items-start gap-2">
                <PenLine size={18} className="text-emerald-600 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-sm font-medium text-slate-800">Insertar firma en todas las plantillas</p>
                  <p className="text-xs text-slate-500 mt-0.5">
                    Agrega <code className="bg-slate-100 px-1 py-0.5 rounded text-[11px] text-emerald-700">{'{Firma_Notificacion_Global}'}</code> al pie de las plantillas que aún no la tengan. Las que ya la incluyen se omiten.
                  </p>
                </div>
              </div>
              <Button
                onClick={handleAppendSignatureToTemplates}
                disabled={appendingSignature}
                className="bg-emerald-600 hover:bg-emerald-700 text-white flex-shrink-0"
                data-testid="append-signature-button"
              >
                <PenLine size={16} className="mr-2" />
                {appendingSignature ? 'Aplicando...' : 'Homologar plantillas'}
              </Button>
            </div>
          </div>

          {/* ===== Configuración General (menú colapsable) ===== */}
          <div className="bg-white rounded-lg border border-slate-200 mb-6 overflow-hidden" data-testid="general-config-section">
            <button
              type="button"
              onClick={() => setGeneralConfigOpen(v => !v)}
              aria-expanded={generalConfigOpen}
              className="w-full flex items-center justify-between gap-3 p-6 text-left hover:bg-slate-50 transition-colors"
              data-testid="general-config-toggle"
            >
              <div className="flex items-start gap-2 min-w-0">
                <Settings2 size={24} className="text-slate-700 flex-shrink-0 mt-0.5" />
                <div className="min-w-0">
                  <h2 className="text-xl font-semibold text-slate-900 font-manrope">Configuración General</h2>
                  <p className="text-slate-600 text-sm mt-0.5">
                    Footer global, correos, calendario laboral, notificaciones, Otras Acciones, SLA, respaldos, usuarios conectados y refresco del embudo.
                  </p>
                </div>
              </div>
              <ChevronDown size={22} className={`text-slate-400 flex-shrink-0 transition-transform duration-200 ${generalConfigOpen ? 'rotate-180' : ''}`} />
            </button>
          </div>

          {generalConfigOpen && (
          <div data-testid="general-config-body">
          {/* ===== Grid moderno de accesos de configuración (2 por fila) ===== */}
          {(() => {
            let isAdminUser = false;
            let isAuditor = false;
            try {
              const u = JSON.parse(localStorage.getItem('user') || '{}');
              isAdminUser = u?.role === 'admin' || u?.is_admin === true;
              isAuditor = isAdminUser || (u?.special_permissions || []).includes('configuracion:auditor');
            } catch { /* noop */ }

            const ACCENTS = {
              slate:   { chip: 'bg-slate-100 text-slate-600',     ring: 'hover:border-slate-300' },
              blue:    { chip: 'bg-blue-100 text-blue-600',       ring: 'hover:border-blue-300' },
              indigo:  { chip: 'bg-indigo-100 text-indigo-600',   ring: 'hover:border-indigo-300' },
              sky:     { chip: 'bg-sky-100 text-sky-600',         ring: 'hover:border-sky-300' },
              violet:  { chip: 'bg-violet-100 text-violet-600',   ring: 'hover:border-violet-300' },
              emerald: { chip: 'bg-emerald-100 text-emerald-600', ring: 'hover:border-emerald-300' },
              rose:    { chip: 'bg-rose-100 text-rose-600',       ring: 'hover:border-rose-300' },
            };

            const tiles = [
              { key: 'security', adminOnly: true, icon: ShieldCheck, accent: 'emerald', title: 'Seguridad y Control de Acceso', desc: 'Políticas de contraseñas, bloqueo por intentos fallidos y 2FA por correo.', route: '/settings/security', testid: 'open-security-policy-btn' },
              { key: 'audit-trails', auditorOnly: true, icon: ScrollText, accent: 'slate', title: 'Pistas de Auditoría', desc: 'Consulta global de creaciones, modificaciones y eliminaciones con visor de diferencias.', route: '/settings/audit-trails', testid: 'open-audit-trails-tile' },
              { key: 'footer', icon: FileText, accent: 'slate', title: 'Footer Global', desc: 'Pie de página institucional anexado a cada correo del ecosistema.', route: '/settings/email-footer', testid: 'open-email-footer-btn' },
              { key: 'email-templates', icon: FileCode, accent: 'blue', title: 'Plantillas de Correo Electrónico', desc: 'Gestor y editor de las plantillas HTML predeterminadas del sistema por sede.', route: '/settings/email-templates', testid: 'open-email-templates-btn' },
              { key: 'email-history', adminOnly: true, icon: Mail, accent: 'indigo', title: 'Historial de Correos', desc: 'Auditoría de correos despachados con filtros y total de registros.', route: '/settings/email-history', testid: 'open-email-history-btn' },
              { key: 'senders', adminOnly: true, icon: Mail, accent: 'blue', title: 'Remitentes de Correo', desc: 'Direcciones remitentes por área (Proyectos e Integradores).', route: '/settings/email-senders', testid: 'open-email-senders-btn' },
              { key: 'project-default-cc', icon: Mail, accent: 'sky', title: 'CC por Defecto en Proyectos', desc: 'Correos precargados en Destinatarios Adicionales de las notificaciones de Proyectos.', route: '/settings/project-default-cc', testid: 'open-project-default-cc-btn' },
              { key: 'calendar', icon: CalendarDays, accent: 'indigo', title: 'Calendario Laboral', desc: 'Días festivos; los SLAs cuentan solo días hábiles.', route: '/settings/work-calendar', testid: 'open-work-calendar-btn' },
              { key: 'notifications', icon: Bell, accent: 'sky', title: 'Notificaciones Push', desc: '16 eventos con prioridad configurable (campana + toast).', route: '/settings/notifications', testid: 'open-notifications-config-btn' },
              { key: 'action-notifications', icon: ShieldCheck, accent: 'blue', title: 'Acciones de Cotizaciones', desc: 'Destinatarios y plantilla por acción del flujo comercial.', route: '/settings/action-notifications', testid: 'open-action-notifications-btn' },
              { key: 'other-actions', icon: Settings2, accent: 'violet', title: 'Otras Acciones', desc: 'Notificaciones de Nuevos Productos y Proyectos de Integración.', route: '/settings/other-actions', testid: 'open-other-actions-btn' },
              { key: 'project-sla', icon: Gauge, accent: 'emerald', title: 'Tiempos y SLA de Proyectos', desc: 'Matriz del semáforo y disparadores automáticos por etapa.', route: '/settings/project-sla', testid: 'open-project-sla-btn' },
              { key: 'backup', adminOnly: true, icon: DatabaseBackup, accent: 'indigo', title: 'Centro de Respaldos', desc: 'Exporta e importa datos maestros (12 entidades) en JSON/ZIP.', route: '/settings/backup-center', testid: 'open-backup-center-btn' },
              { key: 'connected', adminOnly: true, icon: Wifi, accent: 'rose', title: 'Usuarios Conectados', desc: 'Sesiones activas en tiempo real (auto-refresh cada 15s).', route: '/settings/connected-users', testid: 'open-connected-users-btn' },
              { key: 'inbox-cleanup', adminOnly: true, icon: Inbox, accent: 'rose', title: 'Depuración de Archivos', desc: 'Calcula y depura por periodos registros de Inbox, Notificaciones, Logs de Correo, Bitácora y Sesiones para reducir el peso de la base de datos.', route: '/settings/inbox-cleanup', testid: 'open-inbox-cleanup-btn' },
            ];

            return (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4" data-testid="config-tiles-grid">
                {tiles.filter((t) => (!t.adminOnly || isAdminUser) && (!t.auditorOnly || isAuditor)).map((t) => {
                  const a = ACCENTS[t.accent] || ACCENTS.slate;
                  const Icon = t.icon;
                  return (
                    <button
                      key={t.key}
                      type="button"
                      onClick={() => navigate(t.route)}
                      data-testid={t.testid}
                      className={`group flex items-start gap-3 text-left bg-white rounded-xl border border-slate-200 p-5 transition-all duration-200 hover:shadow-lg hover:-translate-y-0.5 ${a.ring}`}
                    >
                      <div className={`w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 transition-transform duration-200 group-hover:scale-105 ${a.chip}`}>
                        <Icon size={22} />
                      </div>
                      <div className="min-w-0 flex-1">
                        <h3 className="text-base font-semibold text-slate-900 font-manrope leading-tight">{t.title}</h3>
                        <p className="text-xs text-slate-500 mt-1 line-clamp-2">{t.desc}</p>
                      </div>
                      <ChevronRight size={18} className="text-slate-300 group-hover:text-slate-500 group-hover:translate-x-0.5 transition-all flex-shrink-0 mt-1" />
                    </button>
                  );
                })}
              </div>
            );
          })()}

          {/* ===== Zona de Peligro (oculta) — se revela con Ctrl+Shift+Alt+K ===== */}
          {(() => {
            let isAdminUser = false;
            try {
              const u = JSON.parse(localStorage.getItem('user') || '{}');
              isAdminUser = u?.role === 'admin' || u?.is_admin === true;
            } catch { /* noop */ }
            if (!dangerUnlocked || !isAdminUser) return null;
            return (
              <div className="mb-4 rounded-xl border-2 border-rose-300 bg-rose-50 p-5" data-testid="danger-zone-card">
                <div className="flex items-start gap-3">
                  <div className="w-11 h-11 rounded-xl bg-rose-100 text-rose-600 flex items-center justify-center flex-shrink-0">
                    <Trash2 size={22} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <h3 className="text-base font-semibold text-rose-800 font-manrope">Zona de Peligro · Reinicio total</h3>
                    <p className="text-xs text-rose-600 mt-1">
                      Borra TODAS las colecciones de la base de datos, preservando únicamente el usuario y la clave del Administrador (y su acceso). Acción irreversible.
                    </p>
                  </div>
                  <Button
                    onClick={() => { setWipeConfirmText(''); setWipeModalOpen(true); }}
                    className="bg-rose-600 hover:bg-rose-700 text-white flex-shrink-0"
                    data-testid="open-wipe-all-btn"
                  >
                    <Trash2 size={16} className="mr-2" /> Borrar todo (excepto Admin)
                  </Button>
                </div>
              </div>
            );
          })()}

          {/* Modal de confirmación del borrado total */}
          {wipeModalOpen && (
            <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/50 p-4" data-testid="wipe-all-modal">
              <div className="bg-white rounded-xl shadow-2xl max-w-md w-full p-6">
                <div className="flex items-center gap-2 text-rose-700 mb-3">
                  <AlertCircle size={22} />
                  <h3 className="text-lg font-bold">Confirmar reinicio total</h3>
                </div>
                <p className="text-sm text-slate-700">
                  Se eliminarán <b>TODAS las colecciones</b> de la base de datos. Solo se conservará el
                  usuario y la clave del <b>Administrador</b> (y su sesión activa). Esta acción
                  <b> NO se puede deshacer</b>.
                </p>
                <p className="text-sm text-slate-700 mt-3">Para continuar, escribe exactamente <b>BORRAR TODO</b>:</p>
                <Input
                  value={wipeConfirmText}
                  onChange={(e) => setWipeConfirmText(e.target.value)}
                  placeholder="BORRAR TODO"
                  className="mt-2"
                  data-testid="wipe-confirm-input"
                  autoFocus
                />
                <div className="flex justify-end gap-2 mt-5">
                  <Button
                    variant="outline"
                    onClick={() => { setWipeModalOpen(false); setWipeConfirmText(''); }}
                    disabled={wiping}
                    data-testid="wipe-cancel-btn"
                  >
                    Cancelar
                  </Button>
                  <Button
                    onClick={handleWipeAll}
                    disabled={wiping || wipeConfirmText.trim() !== 'BORRAR TODO'}
                    className="bg-rose-600 hover:bg-rose-700 text-white disabled:opacity-50"
                    data-testid="wipe-confirm-btn"
                  >
                    {wiping ? 'Borrando...' : 'Borrar definitivamente'}
                  </Button>
                </div>
              </div>
            </div>
          )}


          {/* Rescatar correos antiguos de la Bitácora (solo admin) */}
          {(() => {
            let isAdminUser = false;
            try {
              const u = JSON.parse(localStorage.getItem('user') || '{}');
              isAdminUser = u?.role === 'admin' || u?.is_admin === true;
            } catch { /* noop */ }
            if (!isAdminUser) return null;
            return (
              <div className="bg-white rounded-xl border border-slate-200 p-5 mb-4 flex items-start gap-3" data-testid="bitacora-backfill-card">
                <div className="w-11 h-11 rounded-xl flex items-center justify-center flex-shrink-0 bg-amber-100 text-amber-600">
                  <RefreshCw size={22} />
                </div>
                <div className="min-w-0 flex-1">
                  <h3 className="text-base font-semibold text-slate-900 font-manrope leading-tight">Rescatar Correos Antiguos</h3>
                  <p className="text-xs text-slate-500 mt-1">Convierte a texto simple legible los correos de la Bitácora de Proyectos que hoy están guardados en HTML. El HTML original se conserva.</p>
                </div>
                <button
                  type="button"
                  onClick={runBitacoraBackfill}
                  disabled={backfillRunning}
                  data-testid="run-bitacora-backfill-btn"
                  className="flex-shrink-0 mt-0.5 inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-amber-500 text-white text-sm font-medium hover:bg-amber-600 disabled:opacity-60 transition-colors"
                >
                  {backfillRunning ? <RefreshCw size={16} className="animate-spin" /> : <RefreshCw size={16} />}
                  {backfillRunning ? 'Rescatando...' : 'Rescatar ahora'}
                </button>
              </div>
            );
          })()}

          {/* Anexos Corporativos de Cotización (movido dentro de Configuración General) */}
          <CorporateAnexosCard />

          {/* Refresco del Reporte de Embudo (Admin) */}
          <FunnelRecalculateCard />
          </div>
          )}

        </div>
      </main>
    </div>
  );
};

export default Settings;

// ========================================================================
// FunnelRecalculateCard — Herramienta admin para refrescar timestamps del
// Reporte de Embudo a partir de status_history / archived_at.
// ========================================================================
function FunnelRecalculateCard() {
  const [running, setRunning] = useState(false);
  const [lastResult, setLastResult] = useState(null);

  const handleRun = async () => {
    if (!window.confirm('¿Refrescar la información del Reporte de Embudo? Este proceso recalcula timestamps históricos a partir del historial de estados. No sobrescribe datos existentes.')) return;
    setRunning(true);
    try {
      const { data } = await api.post('/reports/sales/funnel/recalculate');
      setLastResult(data);
      toast.success(`Refresco completado: ${data.updated}/${data.scanned} cotizaciones actualizadas (${data.fields_added} timestamps)`);
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'Error al ejecutar el refresco');
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="bg-white rounded-lg border border-slate-200 p-6 mb-6" data-testid="funnel-recalculate-card">
      <div className="flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <RefreshCw size={24} className="text-amber-600 flex-shrink-0" />
          <div>
            <h2 className="text-xl font-semibold text-slate-900 font-manrope mb-1">
              Refresco del Reporte de Embudo
            </h2>
            <p className="text-sm text-slate-600 max-w-2xl">
              Herramienta administrativa para reconstruir los timestamps históricos del
              Reporte de Embudo (Enviada / Aprobada / Facturada / Pagada / Entregada) a
              partir del historial de estados y archivado. Útil tras un deploy o
              corrección de fechas hacia atrás.
            </p>
            <Badge variant="secondary" className="bg-amber-100 text-amber-800 mt-2 text-xs">
              Solo Admin · No sobrescribe datos existentes
            </Badge>
            {lastResult && (
              <p className="text-xs text-slate-600 mt-2" data-testid="funnel-recalculate-last-result">
                Último refresco: <strong>{lastResult.scanned}</strong> cotizaciones revisadas,
                <strong> {lastResult.updated}</strong> actualizadas,
                <strong> {lastResult.fields_added}</strong> timestamps añadidos.
              </p>
            )}
          </div>
        </div>
        <Button
          onClick={handleRun}
          disabled={running}
          variant="outline"
          className="flex-shrink-0 border-amber-300 text-amber-700 hover:bg-amber-50"
          data-testid="funnel-recalculate-run-btn"
        >
          {running ? 'Procesando...' : 'Ejecutar refresco'}
          <RefreshCw size={16} className={`ml-2 ${running ? 'animate-spin' : ''}`} />
        </Button>
      </div>
    </div>
  );
}


// ========================================================================
// CorporateAnexosCard — Gestor para subir/actualizar los anexos de tarifas
// (Link de Pago / Tokenizador) que el motor de PDF intercala en cotizaciones.
// ========================================================================
function CorporateAnexosCard() {
  const [anexos, setAnexos] = useState([]);
  const [uploadingKey, setUploadingKey] = useState(null);
  const [open, setOpen] = useState(false);
  const [openCats, setOpenCats] = useState({});
  const [loaded, setLoaded] = useState(false);
  const inputRefs = useRef({});

  const loadAnexos = async () => {
    try {
      const res = await api.get('/config/anexos');
      setAnexos(res.data?.anexos || []);
      setLoaded(true);
    } catch {
      toast.error('No se pudieron cargar los anexos corporativos');
    }
  };

  // Carga diferida: solo se piden los anexos al abrir la sección (menos carga inicial)
  const toggleOpen = () => {
    const next = !open;
    setOpen(next);
    if (next && !loaded) loadAnexos();
  };

  const toggleCat = (cat) => setOpenCats((prev) => ({ ...prev, [cat]: !prev[cat] }));

  const uploadAnexo = async (key, fileList) => {
    const f = fileList?.[0];
    if (!f) return;
    if (!f.name.toLowerCase().endsWith('.pdf')) {
      toast.error('El archivo debe ser un PDF');
      return;
    }
    setUploadingKey(key);
    const toastId = toast.loading('Subiendo anexo...');
    try {
      const fd = new FormData();
      fd.append('file', f);
      const res = await api.post(`/config/anexos/${key}`, fd, { headers: { 'Content-Type': 'multipart/form-data' } });
      toast.dismiss(toastId);
      toast.success(`Anexo actualizado (${res.data?.pages || '?'} página(s))`);
      await loadAnexos();
    } catch (e) {
      toast.dismiss(toastId);
      toast.error(e?.response?.data?.detail || 'Error al subir el anexo');
    } finally {
      setUploadingKey(null);
    }
  };

  const downloadAnexo = async (key, filename) => {
    try {
      const res = await api.get(`/config/anexos/${key}/download`, { responseType: 'blob' });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement('a');
      a.href = url; a.download = filename || `${key}.pdf`; a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast.error('No se pudo descargar el anexo');
    }
  };

  const fmtDate = (iso) => {
    if (!iso) return 'Nunca';
    try { return formatDateTime(iso); } catch { return iso; }
  };

  const grouped = Object.entries(anexos.reduce((acc, a) => { (acc[a.category] = acc[a.category] || []).push(a); return acc; }, {}));

  return (
    <div className="bg-white rounded-lg border border-slate-200 mb-6 overflow-hidden" data-testid="corporate-anexos-section">
      {/* Encabezado clicable (colapsable) */}
      <button
        type="button"
        onClick={toggleOpen}
        aria-expanded={open}
        className="w-full flex items-center justify-between gap-3 p-6 text-left hover:bg-slate-50 transition-colors"
        data-testid="corporate-anexos-toggle"
      >
        <div className="flex items-start gap-2 min-w-0">
          <FileText size={24} className="text-blue-600 flex-shrink-0 mt-0.5" />
          <div className="min-w-0">
            <h2 className="text-xl font-semibold text-slate-900 font-manrope flex items-center gap-2">
              Anexos Corporativos de Cotización
              {loaded && anexos.length > 0 && (
                <Badge className="bg-slate-100 text-slate-600 border-slate-200 font-normal">{anexos.length}</Badge>
              )}
            </h2>
            <p className="text-slate-600 text-sm mt-0.5">
              Actualiza los PDFs corporativos (tarifas, términos y condiciones) sin un nuevo despliegue. Solo PDF.
            </p>
          </div>
        </div>
        <ChevronDown size={22} className={`text-slate-400 flex-shrink-0 transition-transform duration-200 ${open ? 'rotate-180' : ''}`} />
      </button>

      {/* Cuerpo desplegable */}
      {open && (
        <div className="px-6 pb-6 border-t border-slate-100 pt-4" data-testid="corporate-anexos-body">
          {!loaded ? (
            <div className="flex items-center justify-center py-8 text-slate-400" data-testid="corporate-anexos-loading">
              <RefreshCw size={18} className="animate-spin mr-2" /> Cargando anexos...
            </div>
          ) : grouped.length === 0 ? (
            <p className="text-sm text-slate-400 py-4">No hay anexos configurados.</p>
          ) : (
            <div className="space-y-3">
              {grouped.map(([cat, items]) => {
                const catOpen = !!openCats[cat];
                const configured = items.filter((i) => i.exists).length;
                return (
                  <div key={cat} className="border border-slate-200 rounded-lg overflow-hidden">
                    {/* Encabezado de categoría (colapsable interno) */}
                    <button
                      type="button"
                      onClick={() => toggleCat(cat)}
                      aria-expanded={catOpen}
                      className="w-full flex items-center justify-between gap-2 px-4 py-2.5 bg-slate-50 hover:bg-slate-100 transition-colors text-left"
                      data-testid={`anexo-cat-toggle-${cat}`}
                    >
                      <span className="flex items-center gap-2 text-sm font-semibold text-slate-700 uppercase tracking-wide">
                        <ChevronRight size={16} className={`text-slate-400 transition-transform duration-200 ${catOpen ? 'rotate-90' : ''}`} />
                        {cat}
                      </span>
                      <Badge className="bg-white text-slate-500 border-slate-200 font-normal">{configured}/{items.length}</Badge>
                    </button>
                    {catOpen && (
                      <div className="p-3 space-y-3" data-testid={`anexo-cat-body-${cat}`}>
                        {items.map((a) => (
                          <div key={a.key} className="border border-slate-200 rounded-lg p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3" data-testid={`anexo-row-${a.key}`}>
                            <div className="min-w-0">
                              <div className="flex items-center gap-2">
                                <span className="font-medium text-slate-800 text-sm">{a.label}</span>
                                {a.exists ? (
                                  <Badge className="bg-emerald-100 text-emerald-700 border-emerald-200">{a.pages || '?'} pág.</Badge>
                                ) : (
                                  <Badge className="bg-red-100 text-red-700 border-red-200">Sin archivo</Badge>
                                )}
                              </div>
                              <p className="text-xs text-slate-500 mt-1">{a.description}</p>
                              <p className="text-xs text-slate-400 mt-1">
                                Última actualización: {fmtDate(a.updated_at)}{a.updated_by ? ` · por ${a.updated_by}` : ''}
                              </p>
                            </div>
                            <div className="flex items-center gap-2 flex-shrink-0">
                              {a.exists && (
                                <Button size="sm" variant="outline" onClick={() => downloadAnexo(a.key, a.filename)} data-testid={`anexo-download-${a.key}`}>
                                  <Download size={16} className="mr-1.5" /> Descargar
                                </Button>
                              )}
                              <input
                                type="file"
                                ref={(el) => { inputRefs.current[a.key] = el; }}
                                onChange={(e) => uploadAnexo(a.key, e.target.files)}
                                accept=".pdf,application/pdf"
                                className="hidden"
                                data-testid={`anexo-file-input-${a.key}`}
                              />
                              <Button
                                size="sm"
                                onClick={() => inputRefs.current[a.key]?.click()}
                                disabled={uploadingKey === a.key}
                                className="bg-blue-600 hover:bg-blue-700 text-white"
                                data-testid={`anexo-upload-${a.key}`}
                              >
                                <Upload size={16} className="mr-1.5" />
                                {uploadingKey === a.key ? 'Subiendo...' : 'Reemplazar'}
                              </Button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
