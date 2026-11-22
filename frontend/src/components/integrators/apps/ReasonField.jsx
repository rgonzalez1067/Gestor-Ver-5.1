import { Textarea } from '../../ui/textarea';
import { ShieldAlert } from 'lucide-react';

export const ReasonField = ({ value, onChange, testId }) => (
  <div className="rounded-md border border-amber-200 bg-amber-50 p-3" data-testid={`${testId}-wrap`}>
    <p className="text-xs font-semibold text-amber-800 flex items-center gap-1.5 mb-1.5"><ShieldAlert size={13} /> Motivo de la modificación * <span className="font-normal">(mínimo 10 caracteres, queda en bitácora y auditoría)</span></p>
    <Textarea rows={2} value={value} onChange={(e) => onChange(e.target.value)} placeholder="Ej: Se habilitó Pago Móvil tras la certificación complementaria del 12/05" className="bg-white text-sm" data-testid={testId} />
  </div>
);

export const reasonError = (needed, reason) => (needed && (reason || '').trim().length < 10 ? 'El motivo es obligatorio (mínimo 10 caracteres)' : null);
