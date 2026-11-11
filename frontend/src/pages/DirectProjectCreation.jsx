import { useState, useEffect, useMemo, useRef, forwardRef, useImperativeHandle } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Plus, Trash2, Save, Upload, FileSpreadsheet, Building2, Boxes, Loader2, FileDown, Search, X, CheckCircle2, AlertCircle, Zap, ShoppingBag, Cpu, Store, Layers, FileText, Server, Network, Paperclip, File as FileIcon, Image as ImageIcon } from 'lucide-react';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Switch } from '../components/ui/switch';
import { Badge } from '../components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Checkbox } from '../components/ui/checkbox';
import { ProcessorLinkBankModal } from '../components/shared/ProcessorLinkBankModal';
import { DirectParamsCard } from '../components/projects/direct/DirectParamsCard';
import { DirectTechFields } from '../components/projects/direct/DirectTechFields';
import { toast } from 'sonner';
import api from '../utils/api';
import { PhaseTag } from '../components/PhaseTag';
import { getProductStatus } from '../utils/bankProductStatus';
import { integratorModalityMatch, shouldShowIntegrationBadge, integrationTypesForName, formatIntegrationBadge, isSelectableIntegrator, isInProcessName } from '../utils/integratorModality';
import { usePermission } from '../hooks/usePermission';

const QUOTE_TYPES = [
  { id: 'VPOS', label: 'VPOS', avail: 'vpos_available' },
  { id: 'MPOS', label: 'MPOS', avail: 'mpos_available' },
  { id: 'GATEWAY', label: 'Payment Gateway', avail: 'gateway_available' },
  { id: 'LINK_PAGO', label: 'Link de Pago', avail: 'link_available' },
];
const REQUIRES_HW = (qt) => qt === 'VPOS' || qt === 'MPOS';
const AVAIL_FIELD = (qt) => (QUOTE_TYPES.find((x) => x.id === qt) || {}).avail || 'vpos_available';
// Payment Gateway / Link de Pago: productos virtuales (sin cajas físicas, sin
// multitienda/multi-rif; integradores filtrados por certificación PG).
const PG_LIKE = (qt) => qt === 'GATEWAY' || qt === 'LINK_PAGO';

/* Anexos del Proyecto Directo — tipos y tamaño permitidos (validados también en backend). */
const DP_ACCEPT = '.pdf,.jpg,.jpeg,.png,.webp,.doc,.docx,.xls,.xlsx,.csv';
const DP_ALLOWED_EXTS = ['pdf', 'jpg', 'jpeg', 'png', 'webp', 'doc', 'docx', 'xls', 'xlsx', 'csv'];
const DP_MAX_BYTES = 10 * 1024 * 1024;
const DP_ATTACH_CATEGORIES = ['Orden de Compra', 'Factura', 'Nota de Entrega', 'Otros'];

function formatBytes(bytes) {
  if (!bytes) return '—';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function attachIcon(name) {
  const ext = (name || '').split('.').pop().toLowerCase();
  if (['png', 'jpg', 'jpeg', 'webp', 'gif'].includes(ext)) return <ImageIcon size={16} className="text-green-500" />;
  if (['pdf'].includes(ext)) return <FileText size={16} className="text-red-500" />;
  if (['xlsx', 'xls', 'csv'].includes(ext)) return <FileSpreadsheet size={16} className="text-emerald-600" />;
  return <FileIcon size={16} className="text-slate-500" />;
}

/* ------------------------------------------------------------------ */
/* Combobox de clientes con búsqueda — forwardRef para foco externo   */
/* ------------------------------------------------------------------ */
const ClientCombobox = forwardRef(function ClientCombobox({ clients, value, onChange }, externalRef) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState('');
  const ref = useRef(null);
  const buttonRef = useRef(null);

  // Exponemos un .focus() al padre para que tras un guardado exitoso pueda
  // devolver el cursor al primer campo del formulario (Iter38).
  useImperativeHandle(externalRef, () => ({
    focus: () => { buttonRef.current?.focus(); setOpen(true); },
  }));

  useEffect(() => {
    if (!open) return;
    const h = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, [open]);

  const filtered = useMemo(() => {
    const s = q.trim().toLowerCase();
    if (!s) return clients.slice(0, 50);
    return clients.filter((c) =>
      (c.fantasy_name || '').toLowerCase().includes(s) ||
      (c.legal_name || '').toLowerCase().includes(s) ||
      (c.rif || '').toLowerCase().includes(s)
    ).slice(0, 50);
  }, [clients, q]);

  const selected = clients.find((c) => c.client_id === value);

  return (
    <div className="relative" ref={ref} data-testid="dp-client-combobox">
      <button
        ref={buttonRef}
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full h-10 px-3 border border-slate-200 rounded-md bg-white text-left text-sm hover:border-slate-300 focus:border-blue-500 focus:outline-none flex items-center justify-between"
      >
        <span className={selected ? 'text-slate-900 truncate' : 'text-slate-400'}>
          {selected ? (selected.legal_name || selected.fantasy_name) : 'Seleccionar cliente...'}
        </span>
        <Search size={16} className="text-slate-400 flex-shrink-0" />
      </button>
      {open && (
        <div className="absolute z-50 mt-1 w-full max-h-72 bg-white border border-slate-200 rounded-md shadow-xl flex flex-col">
          <div className="p-2 border-b border-slate-100">
            <Input
              autoFocus
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Buscar por nombre, fantasy o RIF..."
              className="h-9"
              data-testid="dp-client-search"
            />
          </div>
          <div className="overflow-y-auto flex-1 py-1">
            {filtered.length === 0 ? (
              <div className="px-3 py-4 text-xs text-slate-400 text-center">Sin resultados</div>
            ) : filtered.map((c) => (
              <button
                key={c.client_id}
                type="button"
                onClick={() => { onChange(c.client_id); setOpen(false); setQ(''); }}
                className="w-full text-left px-3 py-2 hover:bg-blue-50 text-sm border-b border-slate-50 last:border-b-0"
                data-testid={`dp-client-opt-${c.client_id}`}
              >
                <div className="font-medium text-slate-800 truncate">{c.legal_name || c.fantasy_name}</div>
                <div className="text-xs text-slate-500 truncate">{c.fantasy_name || ''} · {c.rif || 'sin RIF'}</div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
});

/* ------------------------------------------------------------------ */
/* Excel uploader (descarga plantilla + upload + entrega items)       */
/* ------------------------------------------------------------------ */
function ExcelUploader({ kind, onParsed, testIdPrefix }) {
  const [busy, setBusy] = useState(false);
  const fileRef = useRef(null);

  const downloadTemplate = async () => {
    try {
      const res = await api.get(`/direct-projects/excel-templates/${kind}`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(res.data);
      const a = document.createElement('a');
      a.href = url;
      a.download = kind === 'serials' ? 'plantilla_seriales.xlsx' : 'plantilla_sucursales.xlsx';
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      toast.error(`Error descargando plantilla: ${e.response?.data?.detail || e.message}`);
    }
  };

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const res = await api.post(`/direct-projects/excel-parse/${kind}`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      const items = res.data?.items || [];
      const errors = res.data?.errors || [];
      if (items.length === 0 && errors.length) {
        toast.error(`Excel sin filas válidas. ${errors[0]}`);
      } else if (errors.length) {
        toast.warning(`Cargadas ${items.length} fila(s) con ${errors.length} aviso(s)`);
      } else {
        toast.success(`${items.length} fila(s) cargada(s) desde Excel`);
      }
      onParsed(items, errors);
    } catch (err) {
      toast.error(`Error al parsear Excel: ${err.response?.data?.detail || err.message}`);
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = '';
    }
  };

  return (
    <div className="flex items-center gap-2">
      <Button variant="outline" size="sm" onClick={downloadTemplate} data-testid={`${testIdPrefix}-download-tpl`}>
        <FileDown size={14} className="mr-1" /> Plantilla
      </Button>
      <Button variant="outline" size="sm" onClick={() => fileRef.current?.click()} disabled={busy} data-testid={`${testIdPrefix}-upload`}>
        {busy ? <Loader2 size={14} className="mr-1 animate-spin" /> : <Upload size={14} className="mr-1" />}
        Cargar Excel
      </Button>
      <input ref={fileRef} type="file" accept=".xlsx" onChange={handleUpload} className="hidden" data-testid={`${testIdPrefix}-file-input`} />
    </div>
  );
}

/* ================================================================== */
/* Página principal                                                   */
/* ================================================================== */
export default function DirectProjectCreation() {
  const navigate = useNavigate();
  const { canEdit, isAdmin } = usePermission('proyectos_directos');

  const [clients, setClients] = useState([]);
  const [banks, setBanks] = useState([]);
  const [integrators, setIntegrators] = useState([]);  // array plano de docs
  const [hardware, setHardware] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [lastCreated, setLastCreated] = useState(null); // {project_number, project_id, dispatched}

  // Anexos cargados ANTES del envío a Implementación. Cada item: {uid, file, category}.
  const [attachments, setAttachments] = useState([]);
  const [uploadingAtt, setUploadingAtt] = useState(false);
  const attachInputRef = useRef(null);

  const addAttachments = (fileList) => {
    const incoming = Array.from(fileList || []);
    const accepted = [];
    incoming.forEach((file) => {
      const ext = (file.name || '').split('.').pop().toLowerCase();
      if (!DP_ALLOWED_EXTS.includes(ext)) {
        toast.error(`"${file.name}": tipo no permitido`);
        return;
      }
      if (file.size > DP_MAX_BYTES) {
        toast.error(`"${file.name}" supera los 10MB`);
        return;
      }
      accepted.push({ uid: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`, file, category: 'Otros' });
    });
    if (accepted.length) setAttachments((prev) => [...prev, ...accepted]);
  };
  const removeAttachment = (uid) => setAttachments((prev) => prev.filter((a) => a.uid !== uid));
  const setAttachmentCategory = (uid, category) => setAttachments((prev) => prev.map((a) => a.uid === uid ? { ...a, category } : a));

  const clientRef = useRef(null);
  const serialsAreaRef = useRef(null);

  /* Form state — INITIAL_FORM se usa también para resetear tras Submit. */
  const INITIAL_FORM = {
    client_id: '',
    economic_group: '',
    fantasy_name: '',
    quote_type: 'VPOS',
    sede: 'PYME',
    cantidad_cajas: 1,
    // Payment Gateway: componentes adicionales (Ficha Técnica sección C). Default No.
    includes_link_pago: false,
    includes_tokenizador: false,
    // Multi-RIF
    project_type: 'simple',            // 'simple' | 'multirif'
    multirif_sponsorship: 'bank',      // 'bank' | 'client' (solo multirif)
    shared_matrix: true,               // ¿todas las tiendas comparten bancos/productos?
    multirif_distribution: [],         // [{ client_id, rif, client_name, boxes, stores, boxes_grid }]
    sponsor_bank_id: '',
    sponsor_bank_name: '',
    sponsor_processor_id: '',
    sponsor_processor_name: '',
    integrator_name: '',
    integrator_id: '',
    integrator_app_name: '',
    pinpad_model: '',
    pinpad_provider: '',      // Patrocinador de Pinpads: '' | 'client' | 'infrastructure' | 'bank'
    pinpad_bank: '',          // Patrocinador de Pinpads (nombre del banco final) — solo si provider='bank'
    pinpad_bank_id: '',       // bank_id seleccionado (para lógica relacional)
    pinpad_processor_id: '',  // si el patrocinador de pinpads pasa por un Procesador
    pinpad_processor_name: '',
    fiscal_printer_model: '',
    server_name: '',          // Configuración Técnica: Multicomercio MSC/MSC2/Otra
    server_name_custom: '',   // Nombre libre cuando server_name === 'Otra'
    communication_type: 'SSL', // SSL | VPN | NO_APLICA (preseleccionado SSL)
    pinpad_serials: [],
    is_multistore: false,
    stores: [],
    boxes_grid: [],
    implementation_instructions: '',
    // Parámetros (Nivel de la Cotización → árbol Grupo/Marca/RIF/Sucursal)
    nivel_cotizacion: '',
    grupo_economico_id: '',
    grupo_economico_name: '',
    scope_tree: [],
    cajas_desglose: true,
    patrocinador_tipo: 'CLIENTE',
    fiscal_printer_custom: false,
  };
  const [form, setForm] = useState(INITIAL_FORM);
  // Patrocinio relacional: sub-modal de asociación Procesador → Banco (homologado
  // con el cotizador). Se abre cuando el Banco Patrocinante elegido es un Procesador.
  const [processorModal, setProcessorModal] = useState({ open: false, processor: null });
  // Sub-modal análogo para el Patrocinador de los Pinpads (Procesador → Banco).
  const [pinpadProcessorModal, setPinpadProcessorModal] = useState({ open: false, processor: null });
  // Modal de envío a Implementación: valida si el cliente ya tiene Implementador
  // en su ficha para informar la herencia (Escenario A) o el estatus "Por Asignar"
  // (Escenario B) antes de despachar el proyecto.
  const [assignModal, setAssignModal] = useState({ open: false, scenario: null, name: '' });

  const set = (patch) => setForm((f) => ({ ...f, ...patch }));
  const isMultirif = false;
  const isPaymentGateway = PG_LIKE(form.quote_type);
  const isScope = REQUIRES_HW(form.quote_type);
  const [scopeKey, setScopeKey] = useState(0);
  const handleQuoteType = (v) => {
    set({
      quote_type: v,
      boxes_grid: [],
      integrator_name: '', integrator_id: '', integrator_app_name: '',
      includes_link_pago: false, includes_tokenizador: false,
      // Cambiar entre VPOS/MPOS y Gateway/Link reinicia el alcance seleccionado.
      ...(REQUIRES_HW(v) !== REQUIRES_HW(form.quote_type)
        ? { client_id: '', scope_tree: [], nivel_cotizacion: '', grupo_economico_id: '', grupo_economico_name: '', cantidad_cajas: 1 } : {}),
    });
    if (REQUIRES_HW(v) !== REQUIRES_HW(form.quote_type)) setScopeKey((k) => k + 1);
    setReelBank(''); setReelChecked({});
  };

  /* Carga inicial */
  const [servers, setServers] = useState([]);
  const [fiscalPrinters, setFiscalPrinters] = useState([]);
  useEffect(() => {
    const fetchAll = async () => {
      setLoading(true);
      try {
        const [cRes, bRes, iRes, hRes, sRes, fpRes] = await Promise.all([
          api.get('/clients'),
          api.get('/banks'),
          api.get('/integrators'),
          api.get('/hardware'),
          api.get('/servers').catch(() => ({ data: [] })),
          api.get('/fiscal-printers').catch(() => ({ data: [] })),
        ]);
        const sortedClients = [...(cRes.data || [])].sort((a, b) =>
          (a.fantasy_name || a.legal_name || '').localeCompare(b.fantasy_name || b.legal_name || '', 'es', { sensitivity: 'base' })
        );
        setClients(sortedClients);
        setBanks(bRes.data || []);
        setIntegrators(iRes.data || []);
        setHardware(hRes.data || []);
        setServers((sRes.data || []).map((s) => (s.descripcion || s.name || '').trim()).filter(Boolean)
          .sort((a, b) => a.localeCompare(b, 'es', { sensitivity: 'base' })));
        setFiscalPrinters((fpRes.data || []).map((p) => (p.name || '').trim()).filter(Boolean)
          .sort((a, b) => a.localeCompare(b, 'es', { sensitivity: 'base' })));
      } catch (e) {
        toast.error(`Error cargando datos: ${e.response?.data?.detail || e.message}`);
      } finally { setLoading(false); }
    };
    fetchAll();
  }, []);

  /* Auto-completar datos del cliente al seleccionarlo (en el handler de selección,
     no en un effect, para evitar sincronización de estado derivada en efectos). */
  const handleSelectClient = (clientId) => {
    const c = clients.find((x) => x.client_id === clientId);
    set({
      client_id: clientId,
      ...(c ? {
        economic_group: c.economic_group || c.grupo_economico || '',
        fantasy_name: c.fantasy_name || '',
        sede: (c.client_segment || c.sede || 'PYME').toUpperCase(),
      } : {}),
    });
  };

  /* Helpers grilla (reel) */
  const updateBox = (idx, patch) => {
    setForm((f) => {
      const next = [...f.boxes_grid];
      // Al cambiar el banco, limpiar el producto seleccionado (puede no existir en el nuevo banco)
      if (patch.bank_name !== undefined && patch.bank_name !== next[idx].bank_name) {
        next[idx] = { ...next[idx], ...patch, product_name: '' };
      } else {
        next[idx] = { ...next[idx], ...patch };
      }
      return { ...f, boxes_grid: next };
    });
  };
  const removeBoxRow = (idx) => set({ boxes_grid: form.boxes_grid.filter((_, i) => i !== idx) });

  /* ---- Reel de Distribución: número de cajas + selección múltiple por banco ---- */
  const [reelBank, setReelBank] = useState('');
  const [reelChecked, setReelChecked] = useState({}); // { product_name: true }
  // Número de cajas para el lote a agregar. Se precarga con la "Cantidad de Cajas"
  // de la cabecera, pero es EDITABLE para casos en que el lote difiera.
  const [reelQuantity, setReelQuantity] = useState(form.cantidad_cajas || 1);
  // Mientras el operador no haya editado manualmente el número de cajas del Reel,
  // se mantiene sincronizado con la "Cantidad de Cajas" de la cabecera.
  const reelQtyTouched = useRef(false);
  useEffect(() => {
    if (!reelQtyTouched.current) setReelQuantity(form.cantidad_cajas || 1);
  }, [form.cantidad_cajas]);

  const reelBankProducts = useMemo(() => {
    if (!reelBank) return [];
    const bank = banks.find((b) => b.name === reelBank);
    if (!bank || !Array.isArray(bank.products)) return [];
    const availField = AVAIL_FIELD(form.quote_type);
    // Filtrar por disponibilidad y deduplicar por nombre de producto (guard
    // defensivo ante datos con productos repetidos en un mismo banco).
    const seen = new Set();
    return bank.products.filter((p) => {
      if (!p[availField]) return false;
      const key = (p.product_name || '').trim().toLowerCase();
      if (!key || seen.has(key)) return false;
      seen.add(key);
      return true;
    });
  }, [reelBank, banks, form.quote_type]);

  const selectReelBank = (name) => {
    setReelBank(name);
    setReelChecked({});
  };
  const toggleReelProduct = (productName) => {
    setReelChecked((prev) => ({ ...prev, [productName]: !prev[productName] }));
  };
  const reelSelectedCount = useMemo(
    () => Object.values(reelChecked).filter(Boolean).length,
    [reelChecked]
  );
  const reelAllSelected = reelBankProducts.length > 0 && reelSelectedCount === reelBankProducts.length;
  const toggleSelectAllReel = () => {
    if (reelAllSelected) {
      setReelChecked({});
    } else {
      const all = {};
      reelBankProducts.forEach((p) => { all[p.product_name] = true; });
      setReelChecked(all);
    }
  };

  // Agrega al Reel: crea UNA línea por cada producto-banco marcado, con la
  // cantidad de cajas definida para el lote. Luego limpia la selección para
  // continuar cargando el siguiente lote (manteniendo banco y cantidad).
  const addSelectedProductsToReel = () => {
    const chosen = reelBankProducts.filter((p) => reelChecked[p.product_name]);
    const qty = isPaymentGateway ? 1 : Math.max(1, parseInt(reelQuantity) || 1);
    if (!reelBank) { toast.error('Selecciona un banco primero'); return; }
    if (chosen.length === 0) { toast.error('Marca al menos un producto'); return; }
    setForm((f) => ({
      ...f,
      boxes_grid: [
        ...f.boxes_grid,
        ...chosen.map((p) => ({ quantity: qty, bank_name: reelBank, product_name: p.product_name, store_name: '', operational_status: getProductStatus(p) })),
      ],
    }));
    toast.success(
      isPaymentGateway
        ? `${chosen.length} producto(s) agregado(s) a la matriz (${reelBank})`
        : `${chosen.length} línea(s) agregada(s) al Reel (${reelBank}, ${qty} caja(s) c/u)`
    );
    setReelChecked({});
  };

  const totalBoxesInGrid = useMemo(
    () => form.boxes_grid.reduce((acc, b) => acc + (parseInt(b.quantity) || 0), 0),
    [form.boxes_grid]
  );

  /* Multitienda */
  const addStore = () => set({ stores: [...form.stores, { name: '', box_count: 1 }] });
  const removeStore = (idx) => set({ stores: form.stores.filter((_, i) => i !== idx) });
  const updateStore = (idx, patch) => {
    const next = [...form.stores];
    next[idx] = { ...next[idx], ...patch };
    set({ stores: next });
  };
  const totalStoreBoxes = useMemo(() => form.stores.reduce((acc, s) => acc + (parseInt(s.box_count) || 0), 0), [form.stores]);

  /* Seriales Pinpad — Iter38: solo importa el SERIAL; el modelo es opcional. */
  const addSerial = () => set({ pinpad_serials: [...form.pinpad_serials, { modelo: '', serial: '' }] });
  const removeSerial = (idx) => set({ pinpad_serials: form.pinpad_serials.filter((_, i) => i !== idx) });
  const updateSerial = (idx, patch) => {
    const next = [...form.pinpad_serials];
    next[idx] = { ...next[idx], ...patch };
    set({ pinpad_serials: next });
  };
  const clearSerials = () => set({ pinpad_serials: [] });

  /** Carga masiva por TEXT AREA: separa por líneas / comas / punto-y-coma.
   * Cada token no vacío es un serial. El modelo queda en blanco (Iter38). */
  const [bulkSerialsText, setBulkSerialsText] = useState('');
  const importBulkSerials = () => {
    const tokens = bulkSerialsText
      .split(/[\n,;\t]+/)
      .map((t) => t.trim())
      .filter(Boolean);
    if (tokens.length === 0) {
      toast.error('Pega al menos un serial separado por línea o coma');
      return;
    }
    const added = tokens.map((s) => ({ modelo: '', serial: s }));
    set({ pinpad_serials: [...form.pinpad_serials, ...added] });
    setBulkSerialsText('');
    toast.success(`${added.length} serial(es) agregado(s)`);
  };

  /* Cascada Integrador → Apps.
     Solo integradores "Certificado" cuya modalidad de certificación corresponda
     al tipo de proyecto seleccionado (REST=VPOS, MPOS=MPOS, PG=Gateway/Link).
     Homologado con el filtro del Cotizador. */
  const certifiedIntegrators = useMemo(() => {
    const matches = integratorModalityMatch(form.quote_type);
    return integrators.filter(
      (i) => isSelectableIntegrator(i) && matches(i.integration_type)
    );
  }, [integrators, form.quote_type]);

  const integratorNames = useMemo(() => {
    const names = Array.from(new Set(certifiedIntegrators.map((i) => i.name).filter(Boolean)));
    return names.sort((a, b) => a.localeCompare(b, 'es', { sensitivity: 'base' }));
  }, [certifiedIntegrators]);

  const appsForIntegrator = useMemo(() => {
    if (!form.integrator_name) return [];
    return certifiedIntegrators.filter((i) => i.name === form.integrator_name && (i.app_name || '').trim());
  }, [certifiedIntegrators, form.integrator_name]);

  /* Pinpad models — solo Bien + Pinpad/POS. Filtro de negocio por Tipo de
     Proyecto: VPOS → Marca 'Verifone'; MPOS → Marca 'MoreFun'. */
  const pinpadModels = useMemo(() => {
    const qt = (form.quote_type || '').toUpperCase();
    const marcaFilter = qt === 'VPOS' ? 'Verifone' : qt === 'MPOS' ? 'MoreFun' : null;
    return hardware
      .filter((h) => (h.asset_type === 'Bien') && (h.type === 'Pinpad' || h.type === 'POS'))
      .filter((h) => !marcaFilter || h.marca === marcaFilter)
      .map((h) => ({ value: h.name, label: h.name, type: h.type }))
      .sort((a, b) => a.label.localeCompare(b.label, 'es', { sensitivity: 'base' }));
  }, [hardware, form.quote_type]);

  /* Validación pre-envío — Iter38 reglas actualizadas:
     - Grilla INDEPENDIENTE de cantidad_cajas (no se valida la suma).
     - Cantidad de Cajas (cabecera) = cantidad de seriales Pinpad (solo VPOS/MPOS).
     - Multitienda: suma de cajas por sucursal = cantidad_cajas. */
  const errors = useMemo(() => {
    const errs = [];
    if (isScope) {
      if (!form.nivel_cotizacion) errs.push('Selecciona el Nivel de la Cotización (Grupo, Marca o RIF)');
      else if (!form.scope_tree.length) errs.push('Selecciona al menos un RIF');
      form.scope_tree.forEach((r) => {
        if (!(r.stores || []).length) errs.push(`${r.legal_name || r.rif}: selecciona al menos una sucursal`);
      });
      if (form.cajas_desglose) {
        form.scope_tree.forEach((r) => (r.stores || []).forEach((s) => {
          if (!(parseInt(s.boxes) > 0)) errs.push(`${s.name}: indica la cantidad de cajas`);
        }));
      }
    } else if (!form.client_id) errs.push('Debes seleccionar un cliente');
    if (form.patrocinador_tipo === 'BANCO' && !form.sponsor_bank_id) errs.push('Patrocinada por Banco/Ente: selecciona el Banco Patrocinante');
    if (form.fiscal_printer_custom && !(form.fiscal_printer_model || '').trim()) errs.push('Escribe el modelo de la impresora fiscal');
    if (!form.quote_type) errs.push('Debes seleccionar el tipo de proyecto');
    if (!form.cantidad_cajas || form.cantidad_cajas < 1) errs.push('Cantidad de cajas debe ser >= 1');
    // Modelo de Pinpad y Seriales son OPCIONALES (pueden quedar vacíos en la etapa inicial).
    // Solo si se cargan seriales se valida su consistencia con la Cantidad de Cajas.
    if (REQUIRES_HW(form.quote_type)) {
      const n = form.pinpad_serials.length;
      if (n > 0 && n !== Number(form.cantidad_cajas)) {
        errs.push(`Seriales Pinpad cargados (${n}) ≠ Cantidad de Cajas (${form.cantidad_cajas})`);
      }
    }
    if (form.is_multistore) {
      if (form.stores.length === 0) errs.push('Multitienda activado: agrega al menos una sucursal');
      if (totalStoreBoxes !== Number(form.cantidad_cajas)) {
        errs.push(`Suma cajas multitienda (${totalStoreBoxes}) ≠ Cantidad de Cajas (${form.cantidad_cajas})`);
      }
    }

    // === Multi-RIF: validación de distribución jerárquica + cuadre estricto ===
    const mr = form.project_type === 'multirif';
    if (mr) {
      const dist = form.multirif_distribution || [];
      if (dist.length === 0) {
        errs.push('Multi-RIF: agrega al menos un Cliente/RIF');
      } else {
        let sumRifs = 0;
        dist.forEach((r, i) => {
          if (!r.client_id && r.validated !== false) errs.push(`RIF #${i + 1}: selecciona un cliente`);
          const rb = parseInt(r.boxes) || 0;
          sumRifs += rb;
          const ss = (r.stores || []).reduce((a, s) => a + (parseInt(s.boxes) || 0), 0);
          if ((r.stores || []).length === 0) {
            errs.push(`${r.client_name || 'RIF #' + (i + 1)}: agrega al menos una sucursal`);
          }
          if (ss !== rb) {
            errs.push(`${r.client_name || 'RIF #' + (i + 1)}: cajas de sucursales (${ss}) ≠ cajas del RIF (${rb})`);
          }
          if (!form.shared_matrix && (r.boxes_grid || []).length === 0) {
            errs.push(`${r.client_name || 'RIF #' + (i + 1)}: define bancos/productos para este RIF`);
          }
        });
        if (sumRifs !== Number(form.cantidad_cajas)) {
          errs.push(`Suma cajas de RIFs (${sumRifs}) ≠ Cantidad de Cajas global (${form.cantidad_cajas})`);
        }
      }
      // Patrocinio: si es "Banco", debe haber un banco patrocinante seleccionado.
      if (form.multirif_sponsorship === 'bank' && !form.sponsor_bank_id && !form.sponsor_bank_name) {
        errs.push('Multi-RIF (Patrocinada por Banco): selecciona el Banco Patrocinante');
      }
    }

    // Grilla global (Reel): obligatoria EXCEPTO en Multi-RIF con matriz por RIF.
    const gridRequired = !(mr && !form.shared_matrix);
    if (gridRequired && form.boxes_grid.length === 0) {
      errs.push('Agrega al menos una fila a la grilla');
    } else {
      form.boxes_grid.forEach((b, i) => {
        if (!b.bank_name) errs.push(`Fila #${i + 1}: banco requerido`);
        if (!b.product_name) errs.push(`Fila #${i + 1}: producto requerido`);
        if (!b.quantity || b.quantity < 1) errs.push(`Fila #${i + 1}: cantidad >= 1`);
      });
    }
    // Configuración Técnica (obligatoria)
    if (!form.server_name) errs.push('Debes seleccionar el Servidor de Instalación');
    if (form.server_name === 'Otra' && !(form.server_name_custom || '').trim()) {
      errs.push('Debes escribir el nombre del servidor (opción "Otra")');
    }
    if (!form.communication_type) errs.push('Debes seleccionar el Tipo de Comunicación');
    return errs;
  }, [form, totalStoreBoxes]);

  // Gate: al pulsar "Enviar a Implementación" no despachamos de inmediato.
  // Consultamos la ficha del cliente para saber si tiene un Implementador
  // asignado y mostramos el modal correspondiente (A: asignado / B: por asignar).
  const handleSubmit = async () => {
    if (errors.length) {
      toast.error(`Hay ${errors.length} error(es) en el formulario. Revisa.`);
      return;
    }
    setSaving(true);
    try {
      const { data: client } = await api.get(`/clients/${form.client_id}`);
      const implName = (client?.implementer_name || '').trim();
      const implId = client?.implementer_user_id || '';
      if (implId && implName) {
        setAssignModal({ open: true, scenario: 'assigned', name: implName });
      } else {
        setAssignModal({ open: true, scenario: 'unassigned', name: '' });
      }
    } catch (e) {
      // Si no se puede leer la ficha, continuar con el flujo neutro "Por Asignar".
      setAssignModal({ open: true, scenario: 'unassigned', name: '' });
    } finally {
      setSaving(false);
    }
  };

  const doSubmit = async () => {
    setAssignModal({ open: false, scenario: null, name: '' });
    setSaving(true);
    try {
      // Subir anexos en staging (si los hay) antes de crear el proyecto.
      let uploadedAttachments = [];
      if (attachments.length > 0) {
        setUploadingAtt(true);
        try {
          for (const a of attachments) {
            const fd = new FormData();
            fd.append('file', a.file);
            fd.append('category', a.category || 'Otros');
            const { data: ref } = await api.post('/direct-projects/upload-attachment', fd, {
              headers: { 'Content-Type': 'multipart/form-data' },
            });
            uploadedAttachments.push(ref);
          }
        } catch (upErr) {
          toast.error(`Error subiendo anexos: ${upErr.response?.data?.detail || upErr.message}`);
          setUploadingAtt(false);
          setSaving(false);
          return;
        }
        setUploadingAtt(false);
      }

      const payload = { ...form, cantidad_cajas: Number(form.cantidad_cajas), attachments: uploadedAttachments };
      delete payload.equipment_serials;
      // Modelo de Pinpad: cada serial (cargado por Excel, lote o manual) hereda
      // el "Modelo Pinpad" general del proyecto cuando su fila no trae modelo,
      // para que la Matriz de Seriales de la Ficha Técnica muestre el equipo.
      payload.pinpad_serials = (form.pinpad_serials || []).map((s) => ({
        ...s,
        modelo: (s.modelo && String(s.modelo).trim()) ? s.modelo : (form.pinpad_model || ''),
      }));
      // Resolver Servidor de Instalación: si es "Otra" se envía el texto libre.
      payload.server_name = form.server_name === 'Otra'
        ? (form.server_name_custom || '').trim()
        : form.server_name;
      delete payload.server_name_custom;
      if (form.sponsor_bank_id && !form.sponsor_bank_name) {
        const b = banks.find((x) => x.bank_id === form.sponsor_bank_id);
        if (b) payload.sponsor_bank_name = b.name;
      }
      // Multi-RIF y Multitienda son excluyentes: en Multi-RIF la distribución de
      // tiendas viaja en multirif_distribution.
      if (isMultirif) {
        payload.is_multistore = false;
        payload.stores = [];
      } else {
        payload.multirif_distribution = [];
      }
      payload.project_type = 'simple';
      delete payload.fiscal_printer_custom;
      if (form.patrocinador_tipo !== 'BANCO') {
        payload.sponsor_bank_id = '';
        payload.sponsor_bank_name = '';
        payload.sponsor_processor_id = '';
        payload.sponsor_processor_name = '';
      }
      if (isScope) {
        // Datos del cliente principal (primer RIF del árbol) para la cabecera.
        const main = clients.find((c) => c.client_id === form.client_id) || {};
        const first = form.scope_tree[0] || {};
        payload.economic_group = form.grupo_economico_name || main.grupo_economico || main.economic_group || '';
        payload.fantasy_name = first.marca_name || main.fantasy_name || '';
      } else {
        payload.scope_tree = [];
        payload.nivel_cotizacion = 'RIF';
      }
      const res = await api.post('/direct-projects', payload);
      const d = res.data;
      toast.success(
        `Proyecto ${d.project_number} creado ${d.notification?.dispatched ? '· correo enviado' : '· sin notificación configurada'}${d.attachments_count ? ` · ${d.attachments_count} anexo(s)` : ''}`,
        { duration: 6000 }
      );

      // Iter38: Reset integral + foco al primer campo. NO navegamos.
      setLastCreated({
        project_number: d.project_number,
        project_id: d.project_id,
        dispatched: !!d.notification?.dispatched,
        attachments: d.attachments_count || 0,
      });
      setForm(INITIAL_FORM);
      setScopeKey((k) => k + 1);
      setBulkSerialsText('');
      setAttachments([]);
      // Esperar un tick para que el remount del combobox limpie el valor visible.
      setTimeout(() => clientRef.current?.focus(), 50);
    } catch (e) {
      toast.error(`Error: ${e.response?.data?.detail || e.message}`);
    } finally { setSaving(false); }
  };

  if (loading) {
    return <div className="flex items-center justify-center h-64"><Loader2 size={32} className="animate-spin text-blue-600" /></div>;
  }

  if (!canEdit && !isAdmin) {
    return (
      <div className="max-w-2xl mx-auto p-8 text-center">
        <h2 className="text-xl font-semibold text-slate-700">Acceso restringido</h2>
        <p className="text-slate-500 mt-2">No tienes permisos de edición en el módulo Proyectos Directos.</p>
        <Button className="mt-4" onClick={() => navigate('/projects')}>Volver a Proyectos</Button>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-amber-50/30 to-slate-50">
      <div className="max-w-6xl mx-auto p-4 lg:p-6 space-y-5" data-testid="direct-project-page">

      {/* Hero header con gradiente amarillo — alineado con la identidad "Proyecto Directo" */}
      <div className="rounded-xl bg-gradient-to-r from-amber-500 via-orange-500 to-amber-600 shadow-lg px-5 py-4 text-white flex items-center justify-between" data-testid="dp-hero">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate('/projects')} className="text-white hover:bg-white/15" data-testid="dp-back-btn">
            <ArrowLeft size={18} className="mr-1" /> Proyectos
          </Button>
          <div className="h-7 w-px bg-white/30" />
          <div className="flex items-center gap-2">
            <div className="bg-white/20 rounded-lg p-1.5"><Zap size={20} /></div>
            <div>
              <h1 className="text-xl font-bold leading-tight">Proyecto Directo</h1>
              <p className="text-[11px] text-amber-50/90">Implementación sin cotización previa · Carga continua</p>
            </div>
          </div>
        </div>
        {/* Chips informativos */}
        <div className="flex items-center gap-2">
          {!isPaymentGateway && (
          <span className="bg-white/15 text-xs px-3 py-1 rounded-full backdrop-blur-sm flex items-center gap-1.5">
            <Boxes size={12} /> {form.cantidad_cajas || 0} cajas
          </span>
          )}
          {REQUIRES_HW(form.quote_type) && (
            <span className={`text-xs px-3 py-1 rounded-full backdrop-blur-sm flex items-center gap-1.5 ${form.pinpad_serials.length === Number(form.cantidad_cajas) ? 'bg-emerald-400/30 text-white' : 'bg-rose-400/30 text-white'}`}>
              <FileSpreadsheet size={12} /> {form.pinpad_serials.length} seriales
            </span>
          )}
          <span className={`text-xs px-3 py-1 rounded-full backdrop-blur-sm flex items-center gap-1.5 ${errors.length === 0 ? 'bg-emerald-400/30' : 'bg-rose-400/30'}`}>
            {errors.length === 0 ? <CheckCircle2 size={12} /> : <AlertCircle size={12} />}
            {errors.length === 0 ? 'Listo' : `${errors.length} errores`}
          </span>
        </div>
      </div>

      {/* Banner del último proyecto creado (carga continua — Iter38) */}
      {lastCreated && (
        <div className="bg-gradient-to-r from-emerald-50 to-emerald-100/50 border-l-4 border-emerald-500 rounded-md px-4 py-3 flex items-center justify-between shadow-sm" data-testid="dp-last-created-banner">
          <div className="flex items-center gap-3">
            <div className="bg-emerald-500 rounded-full p-1.5"><CheckCircle2 size={18} className="text-white" /></div>
            <div>
              <p className="text-sm font-medium text-emerald-900">
                Proyecto <span className="font-mono font-bold">{lastCreated.project_number}</span> creado correctamente
              </p>
              <p className="text-xs text-emerald-700">
                {lastCreated.dispatched ? '✓ Correo enviado a destinatarios configurados' : '⚠ Notificación no enviada (no hay configuración para el evento)'}
                {lastCreated.attachments > 0 ? ` · ${lastCreated.attachments} anexo(s) adjuntado(s)` : ''}.
                El formulario se reinició para una nueva captura.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button size="sm" variant="outline" onClick={() => navigate(`/projects/${lastCreated.project_id}`)} className="border-emerald-300 text-emerald-700 hover:bg-emerald-100" data-testid="dp-view-last-project">
              Ver Proyecto
            </Button>
            <button onClick={() => setLastCreated(null)} className="text-emerald-700 hover:text-emerald-900 p-1" title="Cerrar"><X size={14} /></button>
          </div>
        </div>
      )}

      <DirectParamsCard
        form={form}
        set={set}
        clients={clients}
        quoteTypes={QUOTE_TYPES}
        isPaymentGateway={isPaymentGateway}
        isScope={isScope}
        scopeKey={scopeKey}
        onQuoteType={handleQuoteType}
        clientPicker={<ClientCombobox ref={clientRef} clients={clients.filter((c) => !c.is_branch)} value={form.client_id} onChange={handleSelectClient} />}
        bankSelect={(
          <div>
            <Label className="text-xs">Banco Patrocinante *</Label>
              <Select value={form.sponsor_bank_id || ''} onValueChange={(v) => {
                const b = banks.find((x) => x.bank_id === v);
                if (b && b.type === 'Procesador') {
                  // Interceptar: designar el banco final vinculado al procesador.
                  setProcessorModal({ open: true, processor: b });
                  return;
                }
                set({ sponsor_bank_id: v, sponsor_bank_name: b?.name || '', sponsor_processor_id: '', sponsor_processor_name: '' });
              }}>
                <SelectTrigger className="h-10" data-testid="dp-sponsor-bank"><SelectValue placeholder="Sin banco" /></SelectTrigger>
                <SelectContent>
                  {banks.map((b) => <SelectItem key={b.bank_id} value={b.bank_id}>{b.name}{b.type === 'Procesador' ? ' · Procesador' : ''}</SelectItem>)}
                </SelectContent>
              </Select>
              {form.sponsor_processor_name && form.sponsor_bank_name && (
                <p className="text-[11px] text-emerald-700 mt-1 font-medium" data-testid="dp-sponsor-composite">
                  Patrocinador: {form.sponsor_processor_name} — {form.sponsor_bank_name}
                </p>
              )}
          </div>
        )}
      />

      {/* Detalles de Integración: Integrador, Aplicativo, Servidor, Impresora Fiscal, Comunicación, Hardware y Seriales */}
      <Card className="border-cyan-100 shadow-sm" data-testid="dp-integration-card">
        <CardHeader className="pb-3 bg-gradient-to-r from-cyan-50 to-cyan-50/30 border-b border-cyan-100 rounded-t-lg">
          <CardTitle className="text-base flex items-center gap-2 text-cyan-900">
            <div className="bg-cyan-500 rounded-md p-1.5"><Server size={14} className="text-white" /></div>
            Detalles de Integración
          </CardTitle>
          <CardDescription className="text-xs text-cyan-700/70">Estos datos se archivan en la Ficha Técnica del proyecto.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 pt-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {/* Cascada Integrador → App: 1 app = auto-selección; 2+ = drop-list obligatorio */}
            <div>
              <Label className="text-xs">Integrador</Label>
              <Select value={form.integrator_name || ''} onValueChange={(v) => {
                // Evaluar apps del integrador para auto-seleccionar (Escenario A) o
                // dejar pendiente la elección manual (Escenario B). Solo entre los
                // integradores certificados compatibles con el tipo de proyecto.
                const apps = certifiedIntegrators.filter((i) => i.name === v && (i.app_name || '').trim());
                const recs = certifiedIntegrators.filter((i) => i.name === v);
                if (v === '__none__') {
                  set({ integrator_name: '', integrator_id: '', integrator_app_name: '' });
                } else if (apps.length === 1) {
                  set({ integrator_name: v, integrator_id: apps[0].integrator_id, integrator_app_name: apps[0].app_name || '' });
                } else if (apps.length === 0 && recs.length === 1) {
                  set({ integrator_name: v, integrator_id: recs[0].integrator_id, integrator_app_name: '' });
                } else {
                  set({ integrator_name: v, integrator_id: '', integrator_app_name: '' });
                }
              }}>
                <SelectTrigger className="h-10" data-testid="dp-integrator"><SelectValue placeholder="Sin integrador" /></SelectTrigger>
                <SelectContent>
                  {form.integrator_name && <SelectItem value="__none__" data-testid="dp-integrator-none">Sin integrador</SelectItem>}
                  {integratorNames.length === 0 ? (
                    <div className="px-3 py-2 text-xs text-slate-400 italic">No hay integradores certificados o en proceso para este tipo de proyecto</div>
                  ) : integratorNames.map((n) => {
                    const badge = shouldShowIntegrationBadge(form.quote_type) ? formatIntegrationBadge(integrationTypesForName(certifiedIntegrators, n)) : '';
                    return (
                      <SelectItem key={n} value={n} data-testid={`dp-integrator-option-${n.trim().replace(/\s+/g, '-').toLowerCase()}`}>
                        <span>{n}</span>
                        {badge && <span className="ml-1.5 text-xs font-semibold text-indigo-600">{badge}</span>}
                        {isInProcessName(certifiedIntegrators, n) && <span className="ml-1.5 text-[10px] px-1.5 py-0.5 rounded bg-amber-100 text-amber-700" data-testid={`dp-integrator-inprocess-${n.trim().replace(/\s+/g, '-').toLowerCase()}`}>En proceso</span>}
                      </SelectItem>
                    );
                  })}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs">Aplicación {form.integrator_name && <span className="text-amber-600">({appsForIntegrator.length})</span>}</Label>
              {appsForIntegrator.length >= 2 ? (
                /* Escenario B: 2+ apps → drop-list obligatorio */
                <Select
                  value={form.integrator_id || ''}
                  onValueChange={(integratorId) => {
                    const apt = integrators.find((i) => i.integrator_id === integratorId);
                    set({ integrator_id: integratorId, integrator_app_name: apt?.app_name || '' });
                  }}
                >
                  <SelectTrigger className="h-10" data-testid="dp-integrator-app">
                    <SelectValue placeholder="Seleccionar app..." />
                  </SelectTrigger>
                  <SelectContent>
                    {appsForIntegrator.map((i) => <SelectItem key={i.integrator_id} value={i.integrator_id}>{i.app_name}</SelectItem>)}
                  </SelectContent>
                </Select>
              ) : (
                /* Escenario A (1 app, auto-rellenada) o sin apps: campo bloqueado */
                <div
                  className="h-10 flex items-center px-3 rounded-md border border-slate-200 bg-slate-50 text-sm text-slate-600"
                  data-testid="dp-integrator-app-locked"
                >
                  {form.integrator_app_name
                    || (!form.integrator_name
                      ? 'Elige integrador primero'
                      : 'Sin apps registradas')}
                </div>
              )}
            </div>
          </div>
          <DirectTechFields form={form} set={set} servers={servers} fiscalPrinters={fiscalPrinters} />
          {/* Hardware y Seriales (solo VPOS/MPOS) */}
          {REQUIRES_HW(form.quote_type) && (
            <div className="border-t border-slate-100 pt-4 space-y-4" data-testid="dp-hw-section">
              <p className="text-sm font-semibold text-emerald-900 flex items-center gap-2"><Cpu size={14} className="text-emerald-600" /> Hardware y Seriales</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <Label className="text-xs">Modelo Pinpad *</Label>
                <Select value={form.pinpad_model} onValueChange={(v) => set({ pinpad_model: v })}>
                  <SelectTrigger className="h-10" data-testid="dp-pinpad-model">
                    <SelectValue placeholder="Seleccionar pinpad..." />
                  </SelectTrigger>
                  <SelectContent className="max-h-72">
                    {pinpadModels.length === 0 ? (
                      <div className="px-3 py-2 text-xs text-slate-400 italic">Sin modelos de Pinpad/POS marcados como Bien en el catálogo</div>
                    ) : pinpadModels.map((m) => (
                      <SelectItem key={m.value} value={m.value}>
                        {m.label} <span className="text-xs text-slate-400 ml-1">[{m.type}]</span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-xs">Patrocinador de Pinpads</Label>
                <Select value={form.pinpad_provider || ''} onValueChange={(v) => {
                  if (v === 'bank') {
                    set({ pinpad_provider: 'bank' });
                  } else {
                    // "El cliente" / "Infraestructura": no llevan banco asociado.
                    set({ pinpad_provider: v, pinpad_bank_id: '', pinpad_bank: '', pinpad_processor_id: '', pinpad_processor_name: '' });
                  }
                }}>
                  <SelectTrigger className="h-10" data-testid="dp-pinpad-provider"><SelectValue placeholder="Seleccionar" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="client">El cliente</SelectItem>
                    <SelectItem value="infrastructure">Infraestructura</SelectItem>
                    <SelectItem value="bank">Un Banco</SelectItem>
                  </SelectContent>
                </Select>
                {form.pinpad_provider === 'bank' && (
                  <div className="mt-2">
                    <Select value={form.pinpad_bank_id || ''} onValueChange={(v) => {
                      const b = banks.find((x) => x.bank_id === v);
                      if (b && b.type === 'Procesador') {
                        // Interceptar: designar el banco final vinculado al procesador.
                        setPinpadProcessorModal({ open: true, processor: b });
                        return;
                      }
                      set({ pinpad_bank_id: v, pinpad_bank: b?.name || '', pinpad_processor_id: '', pinpad_processor_name: '' });
                    }}>
                      <SelectTrigger className="h-10" data-testid="dp-pinpad-bank"><SelectValue placeholder="Seleccionar banco / procesador" /></SelectTrigger>
                      <SelectContent>
                        {banks.map((b) => <SelectItem key={b.bank_id} value={b.bank_id}>{b.name}{b.type === 'Procesador' ? ' · Procesador' : ''}</SelectItem>)}
                      </SelectContent>
                    </Select>
                    {form.pinpad_processor_name && form.pinpad_bank && (
                      <p className="text-[11px] text-emerald-700 mt-1 font-medium" data-testid="dp-pinpad-composite">
                        Patrocinador: {form.pinpad_processor_name} — {form.pinpad_bank}
                      </p>
                    )}
                  </div>
                )}
                {form.pinpad_provider === 'infrastructure' && (
                  <p className="text-[11px] text-amber-700 mt-1" data-testid="dp-pinpad-infra-note">
                    Se enviará un aviso automático al equipo de Infraestructura al crear el proyecto.
                  </p>
                )}
                {form.pinpad_provider === 'client' && (
                  <p className="text-[11px] text-slate-500 mt-1" data-testid="dp-pinpad-client-note">
                    Los Pinpads serán suministrados por el Cliente.
                  </p>
                )}
              </div>
            </div>

            {/* Seriales Pinpad (carga interactiva) — Iter38: solo SERIAL es obligatorio. */}
            <div className="border border-slate-200 rounded-md p-3 bg-slate-50/40">
              <div className="flex items-center justify-between mb-2">
                <div className="font-medium text-sm text-slate-700 flex items-center gap-2">
                  <Boxes size={14} /> Seriales Pinpad
                  {form.pinpad_serials.length > 0 && (
                    <Badge variant="secondary" className={`text-[10px] ${form.pinpad_serials.length === Number(form.cantidad_cajas) ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}`}>
                      {form.pinpad_serials.length} / {form.cantidad_cajas}
                    </Badge>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <ExcelUploader kind="serials" testIdPrefix="dp-pp" onParsed={(items) => set({ pinpad_serials: [...form.pinpad_serials, ...items] })} />
                  <Button size="sm" variant="outline" onClick={addSerial} data-testid="dp-add-pinpad-serial"><Plus size={14} className="mr-1" /> Manual</Button>
                  {form.pinpad_serials.length > 0 && (
                    <Button size="sm" variant="ghost" onClick={clearSerials} className="text-red-600 hover:bg-red-50" data-testid="dp-clear-serials">
                      <Trash2 size={14} className="mr-1" /> Vaciar
                    </Button>
                  )}
                </div>
              </div>
              <p className="text-[11px] text-slate-500 mb-2">
                Solo es necesario el <strong>número de serial</strong>. La cantidad total debe ser igual a <strong>Cantidad de Cajas ({form.cantidad_cajas})</strong>.
              </p>

              {/* Carga rápida por TextArea (un serial por línea / separado por coma o ;) */}
              <div className="mb-3 grid grid-cols-1 md:grid-cols-[1fr_auto] gap-2 items-start">
                <Textarea
                  ref={serialsAreaRef}
                  value={bulkSerialsText}
                  onChange={(e) => setBulkSerialsText(e.target.value)}
                  placeholder={`Pega seriales aquí (uno por línea o separados por coma)\nEj:\nABC123456\nXYZ789012`}
                  rows={3}
                  className="text-xs font-mono"
                  data-testid="dp-bulk-serials-text"
                />
                <Button size="sm" variant="outline" onClick={importBulkSerials} disabled={!bulkSerialsText.trim()} data-testid="dp-bulk-serials-import">
                  <Plus size={14} className="mr-1" /> Agregar al lote
                </Button>
              </div>

              <div className="space-y-1.5 max-h-72 overflow-y-auto pr-1">
                {form.pinpad_serials.length === 0 ? (
                  <p className="text-xs text-slate-400 italic">Sin seriales cargados</p>
                ) : form.pinpad_serials.map((s, i) => (
                  <div key={i} className="flex gap-2 items-center" data-testid={`dp-pinpad-serial-row-${i}`}>
                    <span className="text-xs text-slate-400 font-mono w-7 text-right">{i + 1}.</span>
                    <Input value={s.serial} onChange={(e) => updateSerial(i, { serial: e.target.value })} placeholder="Serial" className="h-8 text-sm font-mono" />
                    <Button size="sm" variant="ghost" onClick={() => removeSerial(i)} className="text-red-600" data-testid={`dp-remove-serial-${i}`}><Trash2 size={14} /></Button>
                  </div>
                ))}
              </div>
            </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Card 5: Reel de distribución de cajas
          (oculto en Multi-RIF con matriz POR RIF: cada RIF tiene su propia matriz) */}
      {(!isMultirif || form.shared_matrix) && (
      <Card className="border-amber-100 shadow-sm">
        <CardHeader className="pb-3 bg-gradient-to-r from-amber-50 to-amber-50/30 border-b border-amber-100 rounded-t-lg">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-base flex items-center gap-2 text-amber-900">
                <div className="bg-amber-500 rounded-md p-1.5"><Layers size={14} className="text-white" /></div>
                {isPaymentGateway ? 'Matriz de Bancos y Productos Digitales' : 'Reel de Distribución de Cajas'}
              </CardTitle>
              <CardDescription className="text-xs text-amber-800/70 mt-1">
                {isPaymentGateway ? (
                  <>
                    Selecciona los <strong>Bancos / Procesadores</strong> y los <strong>productos digitales</strong> de adquirencia que aplican.
                    El catálogo se filtra por banco + tipo de proyecto (<strong>{(QUOTE_TYPES.find((q) => q.id === form.quote_type) || {}).label}</strong>).
                    <span className="block mt-1 text-amber-700/70">Cada combinación <strong>Banco × Producto</strong> es una asociación de adquirencia digital (sin conteo de cajas físicas).</span>
                  </>
                ) : (
                  <>
                    Cada fila: <strong>Cantidad</strong> + <strong>Banco</strong> + <strong>Producto</strong>.
                    El catálogo de productos se filtra por banco + tipo de proyecto (<strong>{(QUOTE_TYPES.find((q) => q.id === form.quote_type) || {}).label}</strong>).
                    <span className="block mt-1 text-amber-700/70">Esta distribución es <strong>independiente</strong> de la Cantidad de Cajas — captura la realidad comercial (un banco puede tener más productos que cajas físicas).</span>
                  </>
                )}
              </CardDescription>
            </div>
            <p className="text-xs text-amber-900 flex items-center gap-2 bg-white/60 px-3 py-1 rounded-full border border-amber-200" data-testid="dp-reel-counter">
              {isPaymentGateway
                ? <>Combinaciones: <strong className="text-amber-700 text-base">{form.boxes_grid.length}</strong></>
                : <>Total grilla: <strong className="text-amber-700 text-base">{totalBoxesInGrid}</strong></>}
            </p>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Selector por banco + selección múltiple de productos (estilo Cotizador) */}
          <div className="border border-amber-200 rounded-md p-3 bg-amber-50/40 space-y-3" data-testid="dp-reel-selector">
            <div className="grid grid-cols-1 md:grid-cols-[260px_1fr] gap-3 items-start">
              <div className="space-y-3">
                {!isPaymentGateway && (
                <div>
                  <Label className="text-xs text-amber-900">Número de cajas (por producto)</Label>
                  <Input
                    type="number" min="1"
                    value={reelQuantity}
                    onChange={(e) => { reelQtyTouched.current = true; setReelQuantity(Math.max(1, parseInt(e.target.value) || 1)); }}
                    className="h-9 mt-1 bg-white"
                    data-testid="dp-reel-quantity"
                  />
                  <p className="text-[10px] text-amber-700/70 mt-1">Precargado con la Cantidad de Cajas ({form.cantidad_cajas}). Editable por lote.</p>
                </div>
                )}
                <div>
                  <Label className="text-xs text-amber-900">Banco</Label>
                  <Select value={reelBank} onValueChange={selectReelBank}>
                    <SelectTrigger className="h-9 mt-1 bg-white" data-testid="dp-reel-bank-select">
                      <SelectValue placeholder="Selecciona un banco..." />
                    </SelectTrigger>
                    <SelectContent>
                      {banks.map((bk) => <SelectItem key={bk.bank_id} value={bk.name}>{bk.name}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between">
                  <Label className="text-xs text-amber-900">
                    Productos disponibles {reelBank && <span className="text-amber-600">· {reelBankProducts.length}</span>}
                  </Label>
                  {reelBank && reelBankProducts.length > 0 && (
                    <button
                      type="button"
                      onClick={toggleSelectAllReel}
                      className="text-[11px] font-medium text-amber-700 hover:text-amber-900 underline underline-offset-2"
                      data-testid="dp-reel-select-all"
                    >
                      {reelAllSelected ? 'Quitar todos' : 'Seleccionar todos'}
                    </button>
                  )}
                </div>
                {!reelBank ? (
                  <p className="text-xs text-slate-400 italic mt-2">Elige un banco para ver sus productos.</p>
                ) : reelBankProducts.length === 0 ? (
                  <p className="text-xs text-slate-400 italic mt-2">Este banco no tiene productos disponibles para el tipo de proyecto seleccionado.</p>
                ) : (
                  <div className="mt-1 grid grid-cols-1 sm:grid-cols-2 gap-1.5 max-h-56 overflow-y-auto pr-1" data-testid="dp-reel-products">
                    {reelBankProducts.map((p) => (
                      <label
                        key={p.product_name}
                        className="flex items-center gap-2 bg-white border border-slate-200 rounded-md px-2.5 py-1.5 cursor-pointer hover:bg-amber-50 transition-colors"
                        data-testid={`dp-reel-product-${p.product_name}`}
                      >
                        <Checkbox
                          checked={!!reelChecked[p.product_name]}
                          onCheckedChange={() => toggleReelProduct(p.product_name)}
                          data-testid={`dp-reel-check-${p.product_name}`}
                        />
                        <span className="text-xs text-slate-700 flex-1">{p.product_name}</span>
                        <PhaseTag status={getProductStatus(p)} testId={`dp-reel-phase-${p.product_name}`} />
                      </label>
                    ))}
                  </div>
                )}
              </div>
            </div>
            <div className="flex items-center justify-between">
              <p className="text-xs text-amber-800/80" data-testid="dp-reel-selected-info">
                {isPaymentGateway
                  ? `${reelSelectedCount} producto(s) marcado(s)`
                  : `${reelSelectedCount} producto(s) marcado(s)${reelSelectedCount > 0 ? ` · ${reelSelectedCount} línea(s) de ${Math.max(1, parseInt(reelQuantity) || 1)} caja(s)` : ''}`}
              </p>
              <Button
                size="sm"
                onClick={addSelectedProductsToReel}
                disabled={!reelBank || reelSelectedCount === 0}
                className="bg-amber-600 hover:bg-amber-700 text-white"
                data-testid="dp-reel-add-selected"
              >
                <Plus size={14} className="mr-1" /> {isPaymentGateway ? 'Agregar a la matriz' : 'Agregar al Reel'}
              </Button>
            </div>
          </div>

          {/* Grilla resultante del Reel */}
          <div className="border border-slate-200 rounded-md overflow-hidden bg-white">
            <table className="w-full text-sm" data-testid="dp-boxes-grid">
              <thead className="bg-slate-50 border-b border-slate-200">
                <tr>
                  <th className="px-3 py-2 text-left font-medium text-slate-600 w-12">#</th>
                  {!isPaymentGateway && <th className="px-3 py-2 text-left font-medium text-slate-600 w-24">Cantidad</th>}
                  <th className="px-3 py-2 text-left font-medium text-slate-600">Banco</th>
                  <th className="px-3 py-2 text-left font-medium text-slate-600">Producto</th>
                  {form.is_multistore && <th className="px-3 py-2 text-left font-medium text-slate-600">Sucursal</th>}
                  <th className="px-3 py-2 w-12"></th>
                </tr>
              </thead>
              <tbody>
                {form.boxes_grid.length === 0 ? (
                  <tr>
                    <td colSpan={(form.is_multistore ? 6 : 5) - (isPaymentGateway ? 1 : 0)} className="px-3 py-6 text-center text-xs text-slate-400 italic" data-testid="dp-reel-empty">
                      {isPaymentGateway
                        ? 'La matriz está vacía. Selecciona un banco arriba y marca sus productos digitales para agregarlos.'
                        : 'El Reel está vacío. Selecciona un banco arriba y marca sus productos para agregarlos.'}
                    </td>
                  </tr>
                ) : form.boxes_grid.map((b, i) => (
                  <tr key={i} className="border-b border-slate-100" data-testid={`dp-box-row-${i}`}>
                    <td className="px-3 py-1.5 text-slate-400 font-mono">{i + 1}</td>
                    {!isPaymentGateway && (
                    <td className="px-3 py-1.5">
                      <Input
                        type="number" min="1"
                        value={b.quantity}
                        onChange={(e) => updateBox(i, { quantity: Math.max(1, parseInt(e.target.value) || 1) })}
                        className="h-8 text-sm w-20"
                        data-testid={`dp-box-${i}-quantity`}
                      />
                    </td>
                    )}
                    <td className="px-3 py-1.5">
                      <span className="text-sm text-slate-700 font-medium" data-testid={`dp-box-${i}-bank`}>{b.bank_name}</span>
                    </td>
                    <td className="px-3 py-1.5">
                      <span className="text-sm text-slate-700 inline-flex items-center gap-2" data-testid={`dp-box-${i}-product`}>{b.product_name}<PhaseTag status={b.operational_status} testId={`dp-box-${i}-phase`} /></span>
                    </td>
                    {form.is_multistore && (
                      <td className="px-3 py-1.5">
                        <Select value={b.store_name || ''} onValueChange={(v) => updateBox(i, { store_name: v })}>
                          <SelectTrigger className="h-8 text-sm"><SelectValue placeholder="(opcional)" /></SelectTrigger>
                          <SelectContent>
                            {form.stores
                              .filter((s) => (s.name || '').trim())
                              .map((s, si) => <SelectItem key={si} value={s.name}>{s.name}</SelectItem>)}
                          </SelectContent>
                        </Select>
                      </td>
                    )}
                    <td className="px-3 py-1.5">
                      <Button size="sm" variant="ghost" onClick={() => removeBoxRow(i)} className="text-red-600" data-testid={`dp-box-${i}-remove`}><Trash2 size={14} /></Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
      )}

      {/* Card 5.5: Anexos del Proyecto (se adjuntan al correo de Implementación) */}
      <Card className="border-rose-100 shadow-sm" data-testid="dp-attachments-card">
        <CardHeader className="pb-3 bg-gradient-to-r from-rose-50 to-rose-50/30 border-b border-rose-100 rounded-t-lg">
          <CardTitle className="text-base flex items-center gap-2 text-rose-900">
            <div className="bg-rose-500 rounded-md p-1.5"><Paperclip size={14} className="text-white" /></div>
            Anexos del Proyecto <span className="text-xs font-normal text-rose-700/70">(opcional)</span>
          </CardTitle>
          <CardDescription className="text-xs text-rose-700/70">
            Adjunta soportes (orden de compra, imágenes, planillas). Se guardarán en el proyecto y se enviarán al equipo de Implementación junto con la Ficha Técnica. Máx 10MB por archivo · PDF, imágenes, Word, Excel, CSV.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <div
            onDragOver={(e) => { e.preventDefault(); }}
            onDrop={(e) => { e.preventDefault(); addAttachments(e.dataTransfer.files); }}
            className="border-2 border-dashed border-rose-200 rounded-lg p-5 text-center bg-rose-50/30 hover:bg-rose-50/60 transition-colors cursor-pointer"
            onClick={() => attachInputRef.current?.click()}
            data-testid="dp-attach-dropzone"
          >
            <Upload size={22} className="mx-auto text-rose-400 mb-1.5" />
            <p className="text-sm text-slate-600">Arrastra archivos aquí o <span className="text-rose-600 font-semibold">haz clic para seleccionar</span></p>
            <p className="text-[11px] text-slate-400 mt-0.5">Puedes seleccionar varios a la vez</p>
            <input
              ref={attachInputRef}
              type="file"
              multiple
              accept={DP_ACCEPT}
              className="hidden"
              onChange={(e) => { addAttachments(e.target.files); if (attachInputRef.current) attachInputRef.current.value = ''; }}
              data-testid="dp-attach-input"
            />
          </div>

          {attachments.length > 0 && (
            <div className="space-y-1.5" data-testid="dp-attach-list">
              {attachments.map((a) => (
                <div key={a.uid} className="flex items-center gap-2 bg-white border border-slate-200 rounded-md px-3 py-2" data-testid={`dp-attach-item-${a.uid}`}>
                  {attachIcon(a.file.name)}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-700 truncate">{a.file.name}</p>
                    <p className="text-[11px] text-slate-400">{formatBytes(a.file.size)}</p>
                  </div>
                  <Select value={a.category} onValueChange={(v) => setAttachmentCategory(a.uid, v)}>
                    <SelectTrigger className="h-8 w-40 text-xs" data-testid={`dp-attach-cat-${a.uid}`}><SelectValue /></SelectTrigger>
                    <SelectContent>
                      {DP_ATTACH_CATEGORIES.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                    </SelectContent>
                  </Select>
                  <Button size="sm" variant="ghost" onClick={() => removeAttachment(a.uid)} className="text-red-600 h-8 w-8 p-0" data-testid={`dp-attach-remove-${a.uid}`}>
                    <Trash2 size={14} />
                  </Button>
                </div>
              ))}
              <p className="text-[11px] text-slate-500 pt-1" data-testid="dp-attach-count">{attachments.length} anexo(s) listo(s) para enviar.</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Card 6: Instrucciones */}
      <Card className="border-slate-200 shadow-sm">
        <CardHeader className="pb-3 bg-gradient-to-r from-slate-50 to-slate-50/30 border-b border-slate-200 rounded-t-lg">
          <CardTitle className="text-base flex items-center gap-2 text-slate-900">
            <div className="bg-slate-600 rounded-md p-1.5"><FileText size={14} className="text-white" /></div>
            Instrucciones para el Implementador <span className="text-xs font-normal text-slate-500">(opcional)</span>
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Textarea
            value={form.implementation_instructions}
            onChange={(e) => set({ implementation_instructions: e.target.value })}
            placeholder="Notas internas para el equipo de implementación (máx 500 caracteres)"
            rows={4}
            maxLength={500}
            data-testid="dp-instructions"
          />
          <div className="text-xs text-slate-400 text-right mt-1">{(form.implementation_instructions || '').length}/500</div>
        </CardContent>
      </Card>

      {/* Errores + Submit */}
      {errors.length > 0 && (
        <div className="bg-gradient-to-r from-red-50 to-red-100/50 border-l-4 border-red-500 rounded-md p-3 text-sm text-red-800 shadow-sm" data-testid="dp-errors">
          <div className="flex items-center gap-2 mb-1">
            <AlertCircle size={16} className="text-red-600" />
            <strong>Hay errores que debes corregir:</strong>
          </div>
          <ul className="list-disc list-inside mt-1 space-y-0.5 ml-6">
            {errors.slice(0, 6).map((e, i) => <li key={i}>{e}</li>)}
            {errors.length > 6 && <li>... y {errors.length - 6} más</li>}
          </ul>
        </div>
      )}

      <div className="flex items-center justify-end gap-3 sticky bottom-0 bg-gradient-to-r from-white via-white to-amber-50/50 border-t-2 border-amber-200 -mx-4 lg:-mx-6 px-4 lg:px-6 py-3 shadow-[0_-2px_8px_rgba(0,0,0,0.04)] z-10">
        <Button variant="outline" onClick={() => navigate('/projects')} disabled={saving} data-testid="dp-cancel-btn">
          <X size={14} className="mr-1" /> Cancelar
        </Button>
        <Button onClick={handleSubmit} disabled={saving || errors.length > 0} className="bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-600 hover:to-orange-600 text-white shadow-md disabled:from-slate-300 disabled:to-slate-400 disabled:shadow-none" data-testid="dp-submit-btn">
          {saving ? <Loader2 size={14} className="animate-spin mr-1" /> : <Zap size={14} className="mr-1" />}
          Enviar a Implementación
        </Button>
      </div>

      {/* Modal "Enviar a Implementación": Escenario A (asignado) / B (por asignar) */}
      <Dialog open={assignModal.open} onOpenChange={(o) => !o && !saving && setAssignModal({ open: false, scenario: null, name: '' })}>
        <DialogContent className="max-w-md" data-testid="dp-assign-modal">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {assignModal.scenario === 'assigned' ? (
                <><CheckCircle2 size={18} className="text-emerald-600" /> Implementador asignado</>
              ) : (
                <><AlertCircle size={18} className="text-amber-600" /> Sin implementador asignado</>
              )}
            </DialogTitle>
          </DialogHeader>
          {assignModal.scenario === 'assigned' ? (
            <div className="space-y-4">
              <p className="text-sm text-slate-600" data-testid="dp-assign-modal-text">
                Según la ficha del cliente, este proyecto será asignado automáticamente a{' '}
                <strong className="text-emerald-700" data-testid="dp-assign-modal-name">{assignModal.name}</strong>{' '}
                y pasará al área de operaciones como <strong>Asignado</strong>.
              </p>
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setAssignModal({ open: false, scenario: null, name: '' })} disabled={saving} data-testid="dp-assign-cancel-btn">
                  Cancelar
                </Button>
                <Button onClick={doSubmit} disabled={saving} className="bg-emerald-600 hover:bg-emerald-700 text-white" data-testid="dp-assign-confirm-btn">
                  {saving ? <Loader2 size={14} className="animate-spin mr-1" /> : <Zap size={14} className="mr-1" />}
                  {uploadingAtt ? 'Subiendo anexos...' : 'Confirmar y Enviar'}
                </Button>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <p className="text-sm text-slate-600" data-testid="dp-assign-modal-text">
                El cliente no tiene un Implementador asignado en su ficha. El proyecto se enviará al área de
                operaciones con estatus <strong className="text-amber-700">Por Asignar</strong>, en espera de
                asignación técnica.
              </p>
              <div className="flex justify-end">
                <Button onClick={doSubmit} disabled={saving} className="bg-amber-600 hover:bg-amber-700 text-white" data-testid="dp-assign-accept-btn">
                  {saving ? <Loader2 size={14} className="animate-spin mr-1" /> : null}
                  {uploadingAtt ? 'Subiendo anexos...' : 'Aceptar'}
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Sub-modal de Asociación para Patrocinador de Pinpads: Procesador → Banco vinculado */}
      <ProcessorLinkBankModal
        open={pinpadProcessorModal.open}
        processor={pinpadProcessorModal.processor}
        linkedBanks={pinpadProcessorModal.processor ? banks.filter((b) => b.type !== 'Procesador' && b.procesador === pinpadProcessorModal.processor.name) : []}
        onSelect={(b) => {
          const proc = pinpadProcessorModal.processor;
          set({
            pinpad_bank_id: b.bank_id,
            pinpad_bank: b.name,
            pinpad_processor_id: proc?.bank_id || '',
            pinpad_processor_name: proc?.name || '',
          });
          setPinpadProcessorModal({ open: false, processor: null });
        }}
        onClose={() => setPinpadProcessorModal({ open: false, processor: null })}
        description={<>El patrocinador de Pinpads <strong>{pinpadProcessorModal.processor?.name}</strong> es un <strong>Procesador</strong>. Seleccione el banco que operará la transacción para consolidar el patrocinio de hardware.</>}
        testid="dp-pinpad-processor-link"
        linkedTestid="dp-pinpad-processor-linked-bank"
      />

      {/* Sub-modal de Asociación: Procesador → Banco vinculado (patrocinio relacional de implementación) */}
      <ProcessorLinkBankModal
        open={processorModal.open}
        processor={processorModal.processor}
        linkedBanks={processorModal.processor ? banks.filter((b) => b.type !== 'Procesador' && b.procesador === processorModal.processor.name) : []}
        onSelect={(b) => {
          const proc = processorModal.processor;
          set({
            sponsor_bank_id: b.bank_id,
            sponsor_bank_name: b.name,
            sponsor_processor_id: proc?.bank_id || '',
            sponsor_processor_name: proc?.name || '',
          });
          setProcessorModal({ open: false, processor: null });
        }}
        onClose={() => setProcessorModal({ open: false, processor: null })}
        description={<>El patrocinante <strong>{processorModal.processor?.name}</strong> es un <strong>Procesador</strong>. Seleccione el banco que operará la transacción para consolidar el patrocinio.</>}
        testid="dp-processor-link"
        linkedTestid="dp-processor-linked-bank"
      />
    </div>
    </div>
  );
}
