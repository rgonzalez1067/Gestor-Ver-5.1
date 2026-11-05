import { useEffect, useState } from 'react';
import { Check, X } from 'lucide-react';
import api from '../../utils/api';

const SPECIAL = /[!@#$%^&*(),.?":{}|<>\-_=+[\]\\/;'`~]/;

export const buildRules = (minLen) => [
  { key: 'len', label: `Al menos ${minLen} caracteres`, test: (v) => v.length >= minLen },
  { key: 'upper', label: 'Una letra mayúscula', test: (v) => /[A-Z]/.test(v) },
  { key: 'lower', label: 'Una letra minúscula', test: (v) => /[a-z]/.test(v) },
  { key: 'num', label: 'Un número', test: (v) => /[0-9]/.test(v) },
  { key: 'special', label: 'Un carácter especial (!@#$%^&*(),.?":{}|<>)', test: (v) => SPECIAL.test(v) },
];

export const usePasswordPolicy = () => {
  const [policy, setPolicy] = useState({ min_password_length: 12, password_history_count: 5 });
  useEffect(() => {
    api.get('/auth/password-policy').then((r) => setPolicy(r.data)).catch(() => {});
  }, []);
  return { ...policy, rules: buildRules(policy.min_password_length) };
};

export const PasswordChecklist = ({ value, rules, historyCount, testid = 'pwd-rules' }) => (
  <ul className="space-y-1 text-xs" data-testid={testid}>
    {rules.map((r) => {
      const ok = r.test(value || '');
      return (
        <li key={r.key} className={`flex items-center gap-1.5 ${ok ? 'text-emerald-600' : 'text-slate-500'}`} data-testid={`${testid}-${r.key}`}>
          {ok ? <Check size={13} /> : <X size={13} className="text-rose-400" />} {r.label}
        </li>
      );
    })}
    {historyCount > 0 && (
      <li className="text-slate-400 pl-5">No puede repetir sus últimas {historyCount} contraseñas.</li>
    )}
  </ul>
);
