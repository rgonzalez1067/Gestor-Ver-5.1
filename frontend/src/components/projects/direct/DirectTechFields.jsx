import { Server, Network, Printer } from 'lucide-react';
import { Input } from '../../ui/input';
import { Label } from '../../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../ui/select';

const OTHER = '__other__';

const FiscalPrinterField = ({ form, set, fiscalPrinters }) => {
  const custom = form.fiscal_printer_custom || (form.fiscal_printer_model && !fiscalPrinters.includes(form.fiscal_printer_model));
  return (
    <div>
      <Label className="text-xs flex items-center gap-1.5"><Printer size={12} className="text-cyan-600" /> Modelo Impresora Fiscal</Label>
      <Select value={custom ? OTHER : (form.fiscal_printer_model || '__none__')}
        onValueChange={(v) => set(v === OTHER ? { fiscal_printer_custom: true, fiscal_printer_model: '' }
          : { fiscal_printer_custom: false, fiscal_printer_model: v === '__none__' ? '' : v })}>
        <SelectTrigger className="h-10 mt-1" data-testid="dp-fiscal-printer"><SelectValue placeholder="Seleccionar impresora fiscal..." /></SelectTrigger>
        <SelectContent className="max-h-72">
          <SelectItem value="__none__" data-testid="dp-fiscal-printer-none">Sin impresora fiscal</SelectItem>
          {fiscalPrinters.map((p) => (
            <SelectItem key={p} value={p} data-testid={`dp-fiscal-printer-option-${p.replace(/\s+/g, '-').toLowerCase()}`}>{p}</SelectItem>
          ))}
          <SelectItem value={OTHER} data-testid="dp-fiscal-printer-other">Otro (escribir modelo)</SelectItem>
        </SelectContent>
      </Select>
      {custom && (
        <Input className="mt-2" value={form.fiscal_printer_model} placeholder="Escriba el modelo de la impresora..."
          onChange={(e) => set({ fiscal_printer_model: e.target.value })} data-testid="dp-fiscal-printer-custom" />
      )}
    </div>
  );
};

export const DirectTechFields = ({ form, set, servers, fiscalPrinters }) => (
  <>
    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
      <div>
        <Label className="text-xs flex items-center gap-1.5"><Server size={12} className="text-cyan-600" /> Servidor de Instalación <span className="text-red-500">*</span></Label>
        <Select value={form.server_name || ''} onValueChange={(v) => set({ server_name: v, server_name_custom: v === 'Otra' ? form.server_name_custom : '' })}>
          <SelectTrigger className="h-10 mt-1" data-testid="dp-server-name"><SelectValue placeholder="Seleccionar servidor..." /></SelectTrigger>
          <SelectContent>
            {[...(servers.length ? servers : ['Multicomercio MSC', 'Multicomercio MSC2']), 'Otra'].map((opt) => (
              <SelectItem key={opt} value={opt} data-testid={`dp-server-option-${opt.replace(/\s+/g, '-').toLowerCase()}`}>{opt}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        {form.server_name === 'Otra' && (
          <Input value={form.server_name_custom} onChange={(e) => set({ server_name_custom: e.target.value })}
            placeholder="Nombre del servidor (obligatorio)..." className="mt-2" data-testid="dp-server-name-custom" />
        )}
      </div>
      <FiscalPrinterField form={form} set={set} fiscalPrinters={fiscalPrinters} />
    </div>
    <div>
      <Label className="text-xs flex items-center gap-1.5"><Network size={12} className="text-cyan-600" /> Tipo de Comunicación <span className="text-red-500">*</span></Label>
      <div className="flex gap-2 mt-1.5" role="radiogroup" aria-label="Tipo de Comunicación">
        {[['SSL', 'SSL'], ['VPN', 'VPN'], ['NO_APLICA', 'No aplica']].map(([val, label]) => (
          <button key={val} type="button" role="radio" aria-checked={form.communication_type === val}
            onClick={() => set({ communication_type: val })} data-testid={`dp-comm-${val.toLowerCase()}`}
            className={`px-5 py-2 rounded-md text-sm font-semibold border-2 transition-colors ${form.communication_type === val ? 'bg-cyan-600 text-white border-cyan-700 shadow-sm' : 'bg-white text-slate-700 border-slate-200 hover:border-cyan-400'}`}>
            {label}
          </button>
        ))}
      </div>
    </div>
  </>
);
