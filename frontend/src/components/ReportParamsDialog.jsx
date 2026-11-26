import { useEffect, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from './ui/dialog';
import { Button } from './ui/button';
import { RadioGroup, RadioGroupItem } from './ui/radio-group';
import { Label } from './ui/label';

const DEFAULTS = { includeProcessors: 'no', includePreProduction: 'no' };

const Option = ({ value, id, title, hint }) => (
  <label htmlFor={id} className="flex items-start gap-3 p-3 rounded-md border border-slate-200 hover:border-indigo-300 cursor-pointer has-[:checked]:border-indigo-500 has-[:checked]:bg-indigo-50/50 transition-colors">
    <RadioGroupItem value={value} id={id} data-testid={id} className="mt-0.5" />
    <div>
      <div className="text-sm font-medium text-slate-900">{title}</div>
      <div className="text-xs text-slate-500">{hint}</div>
    </div>
  </label>
);

export const ReportParamsDialog = ({ open, onOpenChange, reportName, loading, onGenerate }) => {
  const [params, setParams] = useState(DEFAULTS);
  useEffect(() => { if (open) setParams(DEFAULTS); }, [open]);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg" data-testid="report-params-dialog">
        <DialogHeader>
          <DialogTitle>Parámetros del reporte · {reportName}</DialogTitle>
        </DialogHeader>
        <div className="space-y-5 py-2">
          <div>
            <Label className="text-sm font-semibold text-slate-800">1. Alcance de entidades</Label>
            <RadioGroup value={params.includeProcessors} onValueChange={(v) => setParams({ ...params, includeProcessors: v })} className="mt-2 gap-2">
              <Option value="no" id="report-scope-banks-only" title="Solo Bancos/Entes" hint="Excluye registros clasificados como Procesador" />
              <Option value="yes" id="report-scope-all" title="Bancos/Entes y Procesadores" hint="Incluye la totalidad de las instituciones" />
            </RadioGroup>
          </div>
          <div>
            <Label className="text-sm font-semibold text-slate-800">2. ¿Desea incluir productos en fases no productivas?</Label>
            <RadioGroup value={params.includePreProduction} onValueChange={(v) => setParams({ ...params, includePreProduction: v })} className="mt-2 gap-2">
              <Option value="yes" id="report-phases-yes" title="Sí, incluir todos" hint="Muestra la etiqueta de fase: DESA, SQA, Imple, PreProd, Primer Prod" />
              <Option value="no" id="report-phases-no" title="No" hint="Mostrar únicamente productos en Producción" />
            </RadioGroup>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} data-testid="report-params-cancel">Cancelar</Button>
          <Button
            disabled={loading}
            onClick={() => onGenerate({
              include_processors: params.includeProcessors === 'yes',
              include_pre_production: params.includePreProduction === 'yes',
            })}
            className="bg-indigo-600 hover:bg-indigo-700 text-white"
            data-testid="report-params-generate"
          >
            {loading ? 'Generando...' : 'Generar reporte'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};
