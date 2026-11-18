import { useState } from 'react';
import { toast } from 'sonner';
import api from '../../utils/api';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Popover, PopoverContent, PopoverTrigger } from '../ui/popover';
import { FileSpreadsheet, Download } from 'lucide-react';

// Botón (solo admin) para descargar en Excel las Ediciones Maestras por rango de fechas.
export const MasterEditsReportButton = () => {
  const [from, setFrom] = useState('');
  const [to, setTo] = useState('');
  const [busy, setBusy] = useState(false);
  const download = async () => {
    setBusy(true);
    try {
      const res = await api.get('/project-master-edits/export-xlsx', { params: { date_from: from, date_to: to }, responseType: 'blob' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(res.data);
      a.download = `Ediciones_Maestras_${new Date().toISOString().slice(0, 10)}.xlsx`;
      a.click();
      URL.revokeObjectURL(a.href);
    } catch {
      toast.error('No se pudo generar el reporte de Ediciones Maestras');
    } finally {
      setBusy(false);
    }
  };
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button variant="outline" size="sm" className="border-slate-400 text-slate-700 hover:bg-slate-50" data-testid="master-edits-report-btn">
          <FileSpreadsheet size={14} className="mr-1.5" />Reporte Ediciones Maestras
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-72 space-y-3" data-testid="master-edits-report-popover">
        <p className="text-sm font-semibold text-slate-800">Ediciones Maestras (Excel)</p>
        <div className="grid grid-cols-2 gap-2">
          <div><Label className="text-xs">Desde</Label><Input type="date" value={from} onChange={(e) => setFrom(e.target.value)} className="h-8" data-testid="master-edits-from" /></div>
          <div><Label className="text-xs">Hasta</Label><Input type="date" value={to} onChange={(e) => setTo(e.target.value)} className="h-8" data-testid="master-edits-to" /></div>
        </div>
        <p className="text-[11px] text-slate-500">Vacío = todas las fechas. Una fila por campo cambiado, con su justificación.</p>
        <Button size="sm" className="w-full bg-slate-800 hover:bg-slate-900" onClick={download} disabled={busy} data-testid="master-edits-download-btn">
          <Download size={14} className="mr-1.5" />{busy ? 'Generando…' : 'Descargar Excel'}
        </Button>
      </PopoverContent>
    </Popover>
  );
};
