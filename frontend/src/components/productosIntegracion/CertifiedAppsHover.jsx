import { useState } from 'react';
import { HoverCard, HoverCardContent, HoverCardTrigger } from '../ui/hover-card';
import { Button } from '../ui/button';
import { FileText, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import api from '../../utils/api';

export const CertifiedAppsHover = ({ producto }) => {
  const [apps, setApps] = useState(null);
  const [downloading, setDownloading] = useState(false);
  const load = (open) => {
    if (!open || apps) return;
    api.get(`/productos-integracion/${producto.producto_id}/certificados`).then((r) => setApps(r.data)).catch(() => setApps([]));
  };
  const pdf = async () => {
    setDownloading(true);
    try {
      const r = await api.get(`/productos-integracion/${producto.producto_id}/certificados/pdf`, { responseType: 'blob' });
      const url = URL.createObjectURL(r.data);
      const a = document.createElement('a');
      a.href = url; a.download = `Certificados_${producto.codigo}.pdf`; a.click();
      URL.revokeObjectURL(url);
    } catch { toast.error('Error al generar el PDF'); }
    finally { setDownloading(false); }
  };

  if (!producto.certificados) return <span className="font-semibold text-slate-400">0</span>;
  return (
    <HoverCard openDelay={200} closeDelay={150} onOpenChange={load}>
      <HoverCardTrigger asChild>
        <button type="button" className="font-semibold text-emerald-700 underline decoration-dotted underline-offset-4 hover:text-emerald-900" data-testid={`producto-certificados-${producto.producto_id}`}>{producto.certificados}</button>
      </HoverCardTrigger>
      <HoverCardContent align="center" className="w-[420px] p-0 text-left" data-testid={`producto-certificados-hover-${producto.producto_id}`}>
        <div className="flex items-center justify-between gap-2 px-3 py-2 border-b border-slate-100">
          <p className="text-xs font-semibold text-slate-700 truncate">{producto.nombre} — {producto.certificados} certificado(s)</p>
          <Button size="sm" variant="outline" className="h-7 text-xs shrink-0" disabled={downloading} onClick={pdf} data-testid={`producto-certificados-pdf-${producto.producto_id}`}>
            {downloading ? <Loader2 size={12} className="mr-1 animate-spin" /> : <FileText size={12} className="mr-1 text-red-600" />}PDF
          </Button>
        </div>
        <div className="max-h-72 overflow-y-auto">
          {!apps ? <div className="py-6 flex justify-center"><Loader2 size={16} className="animate-spin text-slate-400" /></div> : (
            <ul className="divide-y divide-slate-100 text-xs">
              {apps.map((a) => (
                <li key={a.integrator_id} className="px-3 py-1.5">
                  <p className="font-medium text-slate-800">{a.name}</p>
                  <p className="text-slate-500 truncate" title={a.app_name}>{a.app_name || '—'}{a.integration_type ? ` · ${a.integration_type}` : ''}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      </HoverCardContent>
    </HoverCard>
  );
};
