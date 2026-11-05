import { useState } from 'react';
import { toast } from 'sonner';
import { KeyRound, Loader2, ArrowLeft, Eye, EyeOff } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import api from '../../utils/api';
import { usePasswordPolicy, PasswordChecklist } from './PasswordRules';

export const ExpiredPasswordStep = ({ changeToken, onDone, onBack }) => {
  const { rules, password_history_count } = usePasswordPolicy();
  const [pwd, setPwd] = useState('');
  const [confirm, setConfirm] = useState('');
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(false);
  const valid = rules.every((r) => r.test(pwd)) && pwd === confirm;

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await api.post('/auth/expired-password/change', { change_token: changeToken, new_password: pwd });
      toast.success(res.data.message);
      onDone();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'No se pudo cambiar la contraseña');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={submit} className="space-y-4" data-testid="expired-password-step">
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-lg bg-amber-100 text-amber-700 flex items-center justify-center shrink-0"><KeyRound size={20} /></div>
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Cambio obligatorio de contraseña</h2>
          <p className="text-sm text-slate-500">Su contraseña venció o debe actualizarse por la nueva política de seguridad.</p>
        </div>
      </div>
      <div>
        <Label>Nueva contraseña</Label>
        <div className="relative mt-1">
          <Input type={show ? 'text' : 'password'} value={pwd} onChange={(e) => setPwd(e.target.value)} className="pr-10" data-testid="expired-new-password" />
          <button type="button" onClick={() => setShow((s) => !s)} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400">{show ? <EyeOff size={16} /> : <Eye size={16} />}</button>
        </div>
      </div>
      <div>
        <Label>Confirmar contraseña</Label>
        <Input type={show ? 'text' : 'password'} value={confirm} onChange={(e) => setConfirm(e.target.value)} className="mt-1" data-testid="expired-confirm-password" />
        {confirm && pwd !== confirm && <p className="text-xs text-rose-600 mt-1" data-testid="expired-mismatch">Las contraseñas no coinciden</p>}
      </div>
      <PasswordChecklist value={pwd} rules={rules} historyCount={password_history_count} testid="expired-pwd-rules" />
      <Button type="submit" disabled={!valid || loading} className="w-full h-11" data-testid="expired-submit-btn">
        {loading ? <Loader2 className="animate-spin" size={18} /> : 'Cambiar contraseña'}
      </Button>
      <button type="button" onClick={onBack} className="text-sm text-slate-500 hover:text-slate-700 flex items-center gap-1" data-testid="expired-back-btn"><ArrowLeft size={14} />Volver al inicio de sesión</button>
    </form>
  );
};
