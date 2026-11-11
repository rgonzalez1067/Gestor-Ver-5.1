import { useEffect, useState } from 'react';
import { Pencil, Save, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { Popover, PopoverContent, PopoverTrigger } from '../ui/popover';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Button } from '../ui/button';
import api from '../../utils/api';

export const GeneratingAreaInfo = ({ rowId }) => {
  const [areas, setAreas] = useState(null);
  const [draft, setDraft] = useState({ pyme_email: '', corp_email: '' });
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.get('/action-notifications/generating-areas').then(r => { setAreas(r.data); setDraft(r.data); }).catch(() => setAreas({}));
  }, []);

  const save = async () => {
    setSaving(true);
    try {
      const { data } = await api.put('/action-notifications/generating-areas', draft);
      setAreas(data);
      setOpen(false);
      toast.success('Buzones del Área generadora actualizados');
    } catch (e) {
      toast.error(e?.response?.data?.detail || 'No se pudo guardar');
    } finally { setSaving(false); }
  };

  return (
    <div className="flex items-start gap-2 text-xs text-slate-600 leading-snug" data-testid={`row-generating-area-info-${rowId}`}>
      <div>
        <p>Ventas Pyme → <span className="font-medium" data-testid="generating-area-pyme-email">{areas?.pyme_email || '…'}</span></p>
        <p>Ventas Corporativas → <span className="font-medium" data-testid="generating-area-corp-email">{areas?.corp_email || '…'}</span></p>
      </div>
      <Popover open={open} onOpenChange={(o) => { setOpen(o); if (o && areas) setDraft(areas); }}>
        <PopoverTrigger asChild>
          <button type="button" title="Editar buzones" className="p-1 rounded hover:bg-slate-100 text-slate-500 hover:text-indigo-600"
            data-testid={`generating-area-edit-btn-${rowId}`}>
            <Pencil size={13} />
          </button>
        </PopoverTrigger>
        <PopoverContent className="w-80 space-y-3" align="start" data-testid="generating-area-popover">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Buzones del Área generadora</p>
          <div>
            <Label className="text-xs">Ventas Pyme</Label>
            <Input value={draft.pyme_email} onChange={e => setDraft(d => ({ ...d, pyme_email: e.target.value }))} data-testid="generating-area-pyme-input" />
          </div>
          <div>
            <Label className="text-xs">Ventas Corporativas</Label>
            <Input value={draft.corp_email} onChange={e => setDraft(d => ({ ...d, corp_email: e.target.value }))} data-testid="generating-area-corp-input" />
          </div>
          <p className="text-[11px] text-slate-500">Aplica a todas las filas "Área generadora" de la matriz.</p>
          <Button size="sm" className="w-full" onClick={save} disabled={saving} data-testid="generating-area-save-btn">
            {saving ? <Loader2 size={14} className="animate-spin mr-1" /> : <Save size={14} className="mr-1" />} Guardar buzones
          </Button>
        </PopoverContent>
      </Popover>
    </div>
  );
};
