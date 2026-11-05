import { useState } from 'react';
import { toast } from 'sonner';
import { ShieldCheck, Loader2, ArrowLeft } from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import api from '../../utils/api';

export const TwoFactorStep = ({ challenge, onSuccess, onBack }) => {
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);

  const verify = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await api.post('/auth/2fa/verify', { challenge_id: challenge.challenge_id, code });
      onSuccess(res.data);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'No se pudo validar el código');
    } finally {
      setLoading(false);
    }
  };

  const resend = async () => {
    setResending(true);
    try {
      await api.post('/auth/2fa/resend', { challenge_id: challenge.challenge_id });
      toast.success('Se envió un nuevo código a su correo');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'No se pudo reenviar el código');
    } finally {
      setResending(false);
    }
  };

  return (
    <form onSubmit={verify} className="space-y-5" data-testid="twofa-step">
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-lg bg-blue-100 text-blue-700 flex items-center justify-center shrink-0"><ShieldCheck size={20} /></div>
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Verificación en dos pasos</h2>
          <p className="text-sm text-slate-500">Enviamos un código de 6 dígitos a <b>{challenge.email_masked}</b>. Vence en {challenge.ttl_minutes} minutos.</p>
        </div>
      </div>
      <Input
        autoFocus inputMode="numeric" value={code}
        onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
        placeholder="000000" className="h-12 text-center text-2xl tracking-[0.5em] font-mono"
        data-testid="twofa-code-input"
      />
      <Button type="submit" disabled={code.length !== 6 || loading} className="w-full h-11" data-testid="twofa-verify-btn">
        {loading ? <Loader2 className="animate-spin" size={18} /> : 'Verificar e ingresar'}
      </Button>
      <div className="flex justify-between text-sm">
        <button type="button" onClick={onBack} className="text-slate-500 hover:text-slate-700 flex items-center gap-1" data-testid="twofa-back-btn"><ArrowLeft size={14} />Volver</button>
        <button type="button" onClick={resend} disabled={resending} className="text-blue-600 hover:underline disabled:opacity-50" data-testid="twofa-resend-btn">
          {resending ? 'Enviando...' : 'Reenviar código'}
        </button>
      </div>
    </form>
  );
};
