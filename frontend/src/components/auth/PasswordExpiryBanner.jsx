import { useEffect, useState } from 'react';
import { AlertTriangle, X } from 'lucide-react';

export const PasswordExpiryBanner = ({ onChange }) => {
  const read = () => {
    if (sessionStorage.getItem('password_expiry_dismissed')) return null;
    const v = parseInt(localStorage.getItem('password_expiry_warning'), 10);
    return Number.isFinite(v) && v > 0 ? v : null;
  };
  const [days, setDays] = useState(read);

  useEffect(() => {
    const h = () => setDays(read());
    window.addEventListener('password-changed', h);
    return () => window.removeEventListener('password-changed', h);
  }, []);

  if (!days) return null;
  const dismiss = () => { sessionStorage.setItem('password_expiry_dismissed', '1'); setDays(null); };

  return (
    <div className="fixed bottom-5 right-5 z-50 max-w-sm rounded-xl border border-amber-300 bg-amber-50 shadow-lg p-4 flex gap-3" data-testid="password-expiry-banner">
      <AlertTriangle className="text-amber-600 shrink-0 mt-0.5" size={20} />
      <div className="text-sm text-amber-900">
        <p className="font-semibold">Su contraseña vencerá en {days} {days === 1 ? 'día' : 'días'}.</p>
        <p className="text-amber-800">Le sugerimos cambiarla ahora.</p>
        <button type="button" onClick={onChange} className="mt-2 text-xs font-semibold text-amber-900 underline" data-testid="password-expiry-change-btn">Cambiar ahora</button>
      </div>
      <button type="button" onClick={dismiss} className="text-amber-500 hover:text-amber-700 self-start" data-testid="password-expiry-dismiss"><X size={16} /></button>
    </div>
  );
};
