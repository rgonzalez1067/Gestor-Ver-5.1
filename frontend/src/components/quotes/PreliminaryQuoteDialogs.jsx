import { useState } from 'react';
import { toast } from 'sonner';
import { Loader2 } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '../ui/dialog';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { ClientCombobox } from '../projects/ClientCombobox';
import api from '../../utils/api';

const EMAIL_RE = /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$/;

export const AssignClientDialog = ({ quote, clients, onClose, onDone }) => {
  const [clientId, setClientId] = useState('');
  const [saving, setSaving] = useState(false);
  const options = clients.filter((c) => !c.is_placeholder);

  const submit = async () => {
    setSaving(true);
    try {
      const r = await api.post(`/quotes/${quote.quote_id}/assign-client`, { client_id: clientId });
      toast.success(`Cotización asignada a ${r.data.client_name}: ${r.data.preliminary_number} → ${r.data.quote_number}`);
      onDone();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'No se pudo asignar el cliente');
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={!!quote} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-md" data-testid="assign-client-dialog">
        <DialogHeader>
          <DialogTitle>Asignar a un cliente · {quote?.quote_number}</DialogTitle>
          <DialogDescription>La cotización tomará el próximo número oficial COT y se habilitará el flujo completo.</DialogDescription>
        </DialogHeader>
        <div className="py-2">
          <Label className="text-xs">Cliente (buscar por nombre o RIF)</Label>
          <div className="mt-1">
            <ClientCombobox clients={options} value={clientId} onSelect={(c) => setClientId(c.client_id)} testid="assign-client" compact />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} data-testid="assign-client-cancel">Cancelar</Button>
          <Button onClick={submit} disabled={!clientId || saving} className="bg-emerald-600 hover:bg-emerald-700" data-testid="assign-client-confirm">
            {saving && <Loader2 className="animate-spin mr-2" size={14} />}Asignar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

export const SendPreliminaryDialog = ({ quote, onClose }) => {
  const [email, setEmail] = useState('');
  const [sending, setSending] = useState(false);
  const valid = EMAIL_RE.test(email.trim());

  const submit = async () => {
    setSending(true);
    try {
      const r = await api.post(`/quotes/${quote.quote_id}/send-preliminary`, { email: email.trim() });
      toast.success(r.data.message);
      setEmail('');
      onClose();
    } catch (e) {
      const d = e.response?.data?.detail;
      toast.error(typeof d === 'string' ? d : 'Correo inválido o no se pudo enviar');
    } finally {
      setSending(false);
    }
  };

  return (
    <Dialog open={!!quote} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-md" data-testid="send-preliminary-dialog">
        <DialogHeader>
          <DialogTitle>Enviar cotización preliminar</DialogTitle>
        </DialogHeader>
        <div className="py-2">
          <Label className="text-xs">Ingrese el correo electrónico del destinatario:</Label>
          <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="correo@empresa.com" className="mt-1" data-testid="send-preliminary-email" />
          {email && !valid && <p className="text-xs text-rose-600 mt-1" data-testid="send-preliminary-invalid">Formato de correo inválido</p>}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} data-testid="send-preliminary-cancel">Cancelar</Button>
          <Button onClick={submit} disabled={!valid || sending} data-testid="send-preliminary-submit">
            {sending && <Loader2 className="animate-spin mr-2" size={14} />}Enviar
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
