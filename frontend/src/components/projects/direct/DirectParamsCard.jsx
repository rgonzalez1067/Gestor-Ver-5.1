import { Layers, Landmark, Building2, Tag } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../ui/card';
import { Input } from '../../ui/input';
import { Label } from '../../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../ui/select';
import { QuoteScopeSelector } from '../../quotes/scope/QuoteScopeSelector';
import { inferTipologia } from '../../quotes/scope/scopeUtils';

const YesNo = ({ label, value, onChange, testId }) => (
  <div>
    <Label className="text-xs">{label} *</Label>
    <Select value={value ? 'si' : 'no'} onValueChange={(v) => onChange(v === 'si')}>
      <SelectTrigger className="h-10" data-testid={testId}><SelectValue /></SelectTrigger>
      <SelectContent><SelectItem value="no">No</SelectItem><SelectItem value="si">Sí</SelectItem></SelectContent>
    </Select>
  </div>
);

const SponsorBlock = ({ form, set, bankSelect }) => (
  <div className="rounded-md border border-slate-200 bg-slate-50/50 p-3 space-y-2" data-testid="dp-sponsor-type-block">
    <Label className="text-xs font-semibold text-slate-800">Tipo de Patrocinio *</Label>
    <div className="flex gap-2 flex-wrap" role="radiogroup">
      {[['CLIENTE', 'Patrocinada por Cliente (Directo)', Building2], ['BANCO', 'Patrocinada por Banco/Ente', Landmark]].map(([k, l, Icon]) => (
        <button key={k} type="button" role="radio" aria-checked={form.patrocinador_tipo === k} data-testid={`dp-sponsor-type-${k.toLowerCase()}`}
          onClick={() => set(k === 'CLIENTE'
            ? { patrocinador_tipo: k, sponsor_bank_id: '', sponsor_bank_name: '', sponsor_processor_id: '', sponsor_processor_name: '' }
            : { patrocinador_tipo: k })}
          className={`px-3 py-1.5 rounded-md text-xs font-semibold border-2 flex items-center gap-1.5 transition-colors ${form.patrocinador_tipo === k ? 'bg-indigo-600 text-white border-indigo-700' : 'bg-white text-slate-700 border-slate-200 hover:border-indigo-400'}`}>
          <Icon size={13} /> {l}
        </button>
      ))}
    </div>
    {form.patrocinador_tipo === 'BANCO' && <div className="max-w-sm">{bankSelect}</div>}
  </div>
);

export const DirectParamsCard = ({ form, set, clients, quoteTypes, isPaymentGateway, isScope, clientPicker, bankSelect, onQuoteType, scopeKey }) => {
  const tipologia = isScope ? (form.scope_tree.length ? inferTipologia(form.scope_tree) : '') : (form.client_id ? 'Monotienda' : '');
  return (
    <Card className="border-indigo-100 shadow-sm" data-testid="dp-params-card">
      <CardHeader className="pb-3 bg-gradient-to-r from-indigo-50 to-indigo-50/30 border-b border-indigo-100 rounded-t-lg">
        <div className="flex items-center justify-between gap-2 flex-wrap">
          <CardTitle className="text-base flex items-center gap-2 text-indigo-900">
            <div className="bg-indigo-500 rounded-md p-1.5"><Layers size={14} className="text-white" /></div>
            Parámetros del Proyecto
          </CardTitle>
          {tipologia && (
            <span className="inline-flex items-center gap-1 text-xs font-bold px-2.5 py-1 rounded-full bg-amber-100 text-amber-800 border border-amber-300" data-testid="dp-tipologia-tag">
              <Tag size={12} /> {tipologia.toUpperCase()}
            </span>
          )}
        </div>
        <CardDescription className="text-xs text-indigo-700/70">Define el nivel y las sucursales; la arquitectura del proyecto se calcula automáticamente.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3 pt-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div>
            <Label className="text-xs">Tipo de Proyecto *</Label>
            <Select value={form.quote_type} onValueChange={onQuoteType}>
              <SelectTrigger className="h-10" data-testid="dp-quote-type"><SelectValue /></SelectTrigger>
              <SelectContent>{quoteTypes.map((qt) => <SelectItem key={qt.id} value={qt.id}>{qt.label}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          {form.quote_type === 'GATEWAY' && (
            <>
              <YesNo label="¿Incluye Link de Pago?" value={form.includes_link_pago} onChange={(v) => set({ includes_link_pago: v })} testId="dp-includes-link-pago" />
              <YesNo label="¿Incluye Tokenizador?" value={form.includes_tokenizador} onChange={(v) => set({ includes_tokenizador: v })} testId="dp-includes-tokenizador" />
            </>
          )}
          {isScope && !form.cajas_desglose && (
            <div>
              <Label className="text-xs">Cantidad de Cajas *</Label>
              <Input type="number" min="1" value={form.cantidad_cajas} data-testid="dp-cantidad-cajas"
                onChange={(e) => set({ cantidad_cajas: e.target.value === '' ? '' : Math.max(1, parseInt(e.target.value) || 1) })} />
            </div>
          )}
          {!isScope && (
            <div className="col-span-2">
              <Label className="text-xs">RIF / Razón Social *</Label>
              {clientPicker}
            </div>
          )}
        </div>
        {isScope && (
          <QuoteScopeSelector key={scopeKey} clients={clients} value={form}
            onChange={(sc) => set({ ...sc, client_id: sc.scope_tree[0]?.client_id || '', ...(sc.cajas_desglose ? { cantidad_cajas: sc.total || 0 } : {}) })} />
        )}
        <SponsorBlock form={form} set={set} bankSelect={bankSelect} />
      </CardContent>
    </Card>
  );
};
