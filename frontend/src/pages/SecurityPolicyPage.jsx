import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, ScrollText, ShieldCheck, KeyRound, Lock, Clock, History, Mail, Save, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Sidebar } from '../components/Sidebar';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Switch } from '../components/ui/switch';
import api from '../utils/api';

const FIELDS = [
  { key: 'password_max_age_days', icon: Clock, title: 'Vigencia de Contraseñas', unit: 'días', hint: 'Al cumplirse, se exige el cambio en el siguiente inicio de sesión.' },
  { key: 'expiry_warning_days', icon: Clock, title: 'Aviso Previo de Vencimiento', unit: 'días', hint: 'Muestra un aviso al iniciar sesión N días antes del vencimiento (menor que la vigencia).' },
  { key: 'password_history_count', icon: History, title: 'Historial de Contraseñas', unit: 'claves', hint: 'Impide repetir las últimas N contraseñas.' },
  { key: 'max_failed_attempts', icon: Lock, title: 'Intentos Fallidos Permitidos', unit: 'intentos', hint: 'Al alcanzarlos, la cuenta se bloquea temporalmente.' },
  { key: 'lockout_minutes', icon: Lock, title: 'Duración del Bloqueo', unit: 'minutos', hint: 'Al culminar, la cuenta se desbloquea automáticamente.' },
  { key: 'min_password_length', icon: KeyRound, title: 'Longitud Mínima de Contraseña', unit: 'caracteres', hint: 'Mínimo permitido: 12. Además exige mayúscula, minúscula, número y carácter especial.', min: 12 },
  { key: 'otp_ttl_minutes', icon: Mail, title: 'Vigencia del Código 2FA', unit: 'minutos', hint: 'Tiempo de caducidad del código enviado por correo.' },
];

const NumberCard = ({ f, value, onChange }) => {
  const Icon = f.icon;
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 flex gap-3" data-testid={`sec-card-${f.key}`}>
      <div className="w-10 h-10 rounded-lg bg-slate-100 text-slate-600 flex items-center justify-center shrink-0"><Icon size={18} /></div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-semibold text-slate-900">{f.title}</p>
        <p className="text-xs text-slate-500 mt-0.5">{f.hint}</p>
        <div className="flex items-center gap-2 mt-2">
          <Input type="number" min={f.min || 0} value={value ?? ''} onChange={(e) => onChange(e.target.value)} className="h-8 w-24 text-sm" data-testid={`sec-input-${f.key}`} />
          <span className="text-xs text-slate-500">{f.unit}</span>
        </div>
      </div>
    </div>
  );
};

export default function SecurityPolicyPage() {
  const navigate = useNavigate();
  const [policy, setPolicy] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.get('/admin/security-policy').then((r) => setPolicy(r.data)).catch((e) => toast.error(e.response?.data?.detail || 'No se pudo cargar la política'));
  }, []);

  const save = async () => {
    setSaving(true);
    try {
      const payload = Object.fromEntries(Object.entries(policy).map(([k, v]) => [k, k === 'two_factor_enabled' ? v : parseInt(v, 10)]));
      const r = await api.put('/admin/security-policy', payload);
      setPolicy(r.data);
      toast.success('Política de seguridad guardada');
    } catch (e) {
      toast.error(e.response?.data?.detail || 'No se pudo guardar');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex min-h-screen bg-slate-50">
      <Sidebar />
      <main className="flex-1 p-8 max-w-5xl" data-testid="security-policy-page">
        <button onClick={() => navigate('/settings')} className="text-sm text-slate-500 hover:text-slate-700 flex items-center gap-1 mb-4" data-testid="sec-back-btn"><ArrowLeft size={14} />Configuración</button>
        <div className="flex items-center gap-3 mb-6">
          <Button variant="outline" onClick={() => navigate('/settings/audit-trails')} className="order-last ml-auto" data-testid="open-audit-trails-btn">
            <ScrollText size={16} className="mr-2" />Pistas de Auditoría
          </Button>
          <div className="w-11 h-11 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center"><ShieldCheck size={22} /></div>
          <div>
            <h1 className="text-2xl font-semibold text-slate-900 font-manrope">Seguridad y Control de Acceso</h1>
            <p className="text-sm text-slate-500">Políticas de contraseñas, bloqueo por intentos fallidos y verificación en dos pasos.</p>
          </div>
        </div>
        {!policy ? <Loader2 className="animate-spin text-slate-400" /> : (
          <>
            <div className="bg-white rounded-xl border border-slate-200 p-4 flex items-center justify-between mb-4" data-testid="sec-card-two_factor_enabled">
              <div className="flex gap-3">
                <div className="w-10 h-10 rounded-lg bg-blue-100 text-blue-700 flex items-center justify-center"><Mail size={18} /></div>
                <div>
                  <p className="text-sm font-semibold text-slate-900">Autenticación de Dos Factores (2FA)</p>
                  <p className="text-xs text-slate-500">Tras validar usuario y contraseña, se envía un código de 6 dígitos al correo del usuario.</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className={`text-xs font-semibold ${policy.two_factor_enabled ? 'text-emerald-700' : 'text-slate-500'}`}>{policy.two_factor_enabled ? 'Activo' : 'Inactivo'}</span>
                <Switch checked={!!policy.two_factor_enabled} onCheckedChange={(v) => setPolicy({ ...policy, two_factor_enabled: v })} data-testid="sec-2fa-switch" />
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {FIELDS.map((f) => <NumberCard key={f.key} f={f} value={policy[f.key]} onChange={(v) => setPolicy({ ...policy, [f.key]: v })} />)}
            </div>
            <div className="flex justify-end mt-6">
              <Button onClick={save} disabled={saving} className="bg-emerald-600 hover:bg-emerald-700" data-testid="sec-save-btn">
                {saving ? <Loader2 className="animate-spin mr-2" size={16} /> : <Save size={16} className="mr-2" />}Guardar políticas
              </Button>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
