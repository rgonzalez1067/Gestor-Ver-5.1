import { useState } from 'react';
import { FileText, FileSpreadsheet, Loader2, ChevronDown, Layers } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '../ui/button';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuLabel, DropdownMenuTrigger } from '../ui/dropdown-menu';
import api from '../../utils/api';

export const BrandsReportButton = ({ brandIds, filtersLabel }) => {
  const [busy, setBusy] = useState(false);
  const download = async (format, grouped = false) => {
    if (!brandIds.length) { toast.error('No hay marcas visibles para el reporte'); return; }
    setBusy(true);
    try {
      const res = await api.post(`/marcas/report?format=${format}${grouped ? '&group_by=group' : ''}`, { brand_ids: brandIds, filters_label: filtersLabel }, { responseType: 'blob' });
      const stamp = new Date().toISOString().slice(0, 10).replace(/-/g, '');
      const url = URL.createObjectURL(res.data);
      const a = document.createElement('a');
      a.href = url; a.download = `Reporte_Marcas_${stamp}${grouped ? '_PorGrupo' : ''}.${format}`;
      document.body.appendChild(a); a.click(); a.remove();
      URL.revokeObjectURL(url);
    } catch {
      toast.error('No se pudo generar el reporte');
    } finally { setBusy(false); }
  };
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="sm" disabled={busy} data-testid="brands-report-btn">
          {busy ? <Loader2 size={14} className="animate-spin mr-1.5" /> : <FileText size={14} className="mr-1.5" />}
          Reporte General ({brandIds.length}) <ChevronDown size={13} className="ml-1 opacity-60" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={() => download('pdf')} data-testid="brands-report-pdf">
          <FileText size={14} className="mr-2 text-red-600" /> Emitir PDF
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => download('xlsx')} data-testid="brands-report-xlsx">
          <FileSpreadsheet size={14} className="mr-2 text-emerald-600" /> Descargar Excel
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuLabel className="text-xs flex items-center gap-1.5 text-muted-foreground"><Layers size={12} /> Agrupado por Grupo Económico</DropdownMenuLabel>
        <DropdownMenuItem onClick={() => download('pdf', true)} data-testid="brands-report-grouped-pdf">
          <FileText size={14} className="mr-2 text-red-600" /> PDF por Grupo
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => download('xlsx', true)} data-testid="brands-report-grouped-xlsx">
          <FileSpreadsheet size={14} className="mr-2 text-emerald-600" /> Excel por Grupo
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
};
