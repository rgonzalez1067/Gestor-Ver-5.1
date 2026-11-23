import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, BellRing, Save } from 'lucide-react';
import { Sidebar } from '../components/Sidebar';
import { Button } from '../components/ui/button';
import { AlertResourceCard } from '../components/settings/AlertResourceCard';
import { useUnreadMessages } from '../context/UnreadMessagesContext';
import { toast } from 'sonner';
import api from '../utils/api';

const RESOURCES = [
  ['push', 'Notificaciones emergentes (arriba a la derecha)', 'Alertas emergentes con sonido de notificaciones, mensajes internos y recordatorios. Aunque se apaguen, siguen llegando a la campana y al Centro de Mensajes.'],
  ['unread_banner', 'Aviso de mensajes pendientes por leer', 'Recuadro rojo «Tiene X mensajes pendientes por leer en su bandeja».'],
];

export default function UiAlertsConfig() {
  const navigate = useNavigate();
  const { refresh } = useUnreadMessages();
  const [data, setData] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.get('/settings/ui-alerts').then((r) => setData(r.data))
      .catch((e) => toast.error(e.response?.data?.detail || 'No se pudo cargar la configuración'));
  }, []);

  const save = async () => {
    setSaving(true);
    try {
      await api.put('/settings/ui-alerts', data.config);
      toast.success('Configuración de avisos guardada');
      refresh();
    } catch (e) { toast.error(e.response?.data?.detail || 'Error al guardar'); }
    finally { setSaving(false); }
  };

  return (
    <div className="flex min-h-screen bg-slate-50">
      <Sidebar />
      <main className="flex-1 p-8" data-testid="ui-alerts-page">
        <div className="max-w-5xl mx-auto space-y-5">
          <Button variant="ghost" size="sm" onClick={() => navigate('/settings')} className="-ml-3" data-testid="back-to-settings">
            <ArrowLeft size={16} className="mr-2" /> Volver a Configuración
          </Button>
          <div className="flex items-start justify-between gap-4">
            <div>
              <h1 className="text-3xl font-bold text-slate-900 font-manrope flex items-center gap-3"><BellRing className="text-rose-600" size={28} />Avisos en Pantalla</h1>
              <p className="text-sm text-slate-500 mt-1">Basta con que un nivel esté apagado (todos, departamento o persona) para que el usuario no vea el aviso. Los cambios se aplican en menos de un minuto.</p>
            </div>
            <Button onClick={save} disabled={!data || saving} className="bg-brand-green-600 hover:bg-brand-green-700 shrink-0" data-testid="ui-alerts-save-btn">
              <Save size={16} className="mr-2" />{saving ? 'Guardando...' : 'Guardar cambios'}
            </Button>
          </div>
          {!data ? <p className="text-sm text-slate-400 py-10 text-center">Cargando...</p> : RESOURCES.map(([rid, title, desc]) => (
            <AlertResourceCard key={rid} rid={rid} title={title} description={desc} rule={data.config[rid]}
              departments={data.departments} users={data.users}
              onChange={(rule) => setData((d) => ({ ...d, config: { ...d.config, [rid]: rule } }))} />
          ))}
        </div>
      </main>
    </div>
  );
}
