import { Label } from './ui/label';
import { Input } from './ui/input';
import { MailPlus } from 'lucide-react';

const EMAIL_RE = /^[^@\s,;<>]+@[^@\s,;<>]+\.[^@\s,;<>]+$/;

export const parseCopyEmails = (raw) => {
  const seen = new Set();
  return (raw || '').split(/[,;\s]+/).map((e) => e.trim()).filter((e) => {
    if (!e || seen.has(e.toLowerCase())) return false;
    seen.add(e.toLowerCase()); return true;
  });
};
export const invalidCopyEmails = (raw) => {
  const list = parseCopyEmails(raw);
  const bad = list.filter((e) => !EMAIL_RE.test(e));
  return list.length > 10 ? [...bad, 'máximo 10 destinatarios'] : bad;
};

// Destinatarios que reciben una copia (BCC) de la comunicación masiva.
export const CopyEmailsField = ({ value, onChange, testid = 'mass-copy-emails' }) => {
  const invalid = invalidCopyEmails(value);
  const count = parseCopyEmails(value).length;
  return (
    <div>
      <Label className="text-sm font-medium flex items-center gap-1"><MailPlus size={14} />Enviar copia a</Label>
      <Input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="correo@megasoft.com.ve (varios separados por coma)"
        className={`mt-1 text-sm ${invalid.length ? 'border-rose-400 focus-visible:ring-rose-300' : ''}`}
        data-testid={testid}
      />
      {invalid.length > 0 ? (
        <p className="text-[11px] text-rose-600 mt-1" data-testid={`${testid}-error`}>Correo inválido: {invalid.join(', ')}</p>
      ) : (
        <p className="text-[11px] text-slate-400 mt-1">
          {count ? `${count} destinatario(s) recibirán una copia oculta (BCC).` : 'Opcional · recibe una copia oculta (BCC) del envío.'}
        </p>
      )}
    </div>
  );
};

export default CopyEmailsField;
