import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { ArrowLeft, Save, X, Plus, Info } from 'lucide-react';
import { Sidebar } from '../components/Sidebar';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import api from '../utils/api';
import { formatDateTime } from '../utils/dateFormat';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export default function ProjectDefaultCcConfig() {
  const navigate = useNavigate();
  const isAdmin = JSON.parse(localStorage.getItem('user') || '{}')?.role === 'admin';
  const [emails, setEmails] = useState([]);
  const [meta, setMeta] = useState({});
  const [draft, setDraft] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.get('/config/project-default-cc').then(({ data }) => { setEmails(data.emails || []); setMeta(data); })
      .catch(() => toast.error('No se pudo cargar la configuración'));
  }, []);

  const add = () => {
    const e = draft.trim().toLowerCase();
    if (!EMAIL_RE.test(e)) { toast.error('Correo inválido'); return; }
    if (!emails.includes(e)) setEmails([...emails, e]);
    setDraft('');
  };
  const save = async () => {
    setSaving(true);
    try {
      const { data } = await api.put('/config/project-default-cc', { emails });
      setMeta(data); toast.success('Destinatarios por defecto guardados');
    } catch (e) { toast.error(e.response?.data?.detail || 'Error al guardar'); }
    finally { setSaving(false); }
  };

  return (
    <div className="flex h-screen bg-slate-50">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto p-6 lg:p-8">
          <Button variant="ghost" size="sm" onClick={() => navigate('/settings')} className="mb-6" data-testid="default-cc-back-btn">
            <ArrowLeft size={18} className="mr-1" />Configuración
          </Button>
          <h1 className="text-3xl font-bold text-slate-900 font-manrope" data-testid="default-cc-title">CC por Defecto en Proyectos</h1>
          <p className="text-slate-600 mt-1 text-sm">Correos que aparecen precargados en "Destinatarios Adicionales (CC)" de las notificaciones y correos de Proyectos. El usuario puede quitarlos antes de enviar.</p>
          {meta.updated_at && <p className="text-xs text-slate-500 mt-2" data-testid="default-cc-updated">Última actualización: {formatDateTime(meta.updated_at)}{meta.updated_by ? ` · por ${meta.updated_by}` : ''}</p>}
          <div className="mt-6 bg-white border border-slate-200 rounded-lg p-5 space-y-4">
            <div className="flex flex-wrap gap-2 min-h-[32px]" data-testid="default-cc-list">
              {emails.length === 0 && <span className="text-sm text-slate-400">Sin correos por defecto</span>}
              {emails.map(e => (
                <span key={e} className="inline-flex items-center gap-1 rounded-full bg-blue-50 border border-blue-200 px-2.5 py-1 text-xs text-blue-800" data-testid={`default-cc-chip-${e}`}>
                  {e}
                  {isAdmin && <button type="button" onClick={() => setEmails(emails.filter(x => x !== e))} className="hover:text-red-600" data-testid={`default-cc-remove-${e}`}><X size={12} /></button>}
                </span>
              ))}
            </div>
            {isAdmin ? (
              <>
                <div className="flex gap-2">
                  <Input value={draft} onChange={e => setDraft(e.target.value)} onKeyDown={e => e.key === 'Enter' && add()} placeholder="correo@megasoft.com.ve" className="h-9" data-testid="default-cc-input" />
                  <Button variant="outline" onClick={add} className="h-9" data-testid="default-cc-add-btn"><Plus size={14} className="mr-1" />Agregar</Button>
                </div>
                <Button onClick={save} disabled={saving} className="bg-brand-green-600 hover:bg-brand-green-700 text-white" data-testid="default-cc-save-btn"><Save size={14} className="mr-1" />Guardar</Button>
              </>
            ) : (
              <p className="flex items-center gap-1 text-xs text-slate-500"><Info size={12} />Solo un administrador puede modificar esta lista.</p>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
