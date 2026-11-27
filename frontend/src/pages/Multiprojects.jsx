import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { toast } from 'sonner';
import { Link2, Search, Rocket, Loader2, Building2, Store, Tag, Users, Cpu, ChevronRight } from 'lucide-react';
import api from '../utils/api';
import { Sidebar } from '../components/Sidebar';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Textarea } from '../components/ui/textarea';

const LEVELS = [{ id: 'grupo', label: 'Grupo Económico' }, { id: 'marca', label: 'Marca' }, { id: 'rif', label: 'RIF' }];

const HierarchyStep = ({ preview }) => {
  const groups = {};
  preview.rifs.forEach(r => { ((groups[r.grupo] ||= {})[r.marca] ||= []).push(r); });
  return (
    <div className="text-sm space-y-2" data-testid="mp-hierarchy">
      <p className="text-xs text-slate-500">Nivel detectado: <b data-testid="mp-level">{preview.level}</b></p>
      {Object.entries(groups).map(([g, marcas]) => (
        <div key={g} className="border border-slate-200 rounded-lg p-3">
          <p className="font-semibold flex items-center gap-1.5"><Users size={14} className="text-indigo-600" />Grupo: {g}</p>
          {Object.entries(marcas).map(([m, rifs]) => (
            <div key={m} className="ml-4 mt-2">
              <p className="font-medium flex items-center gap-1.5"><Tag size={13} className="text-amber-600" />Marca: {m}</p>
              {rifs.map(r => (
                <div key={r.client_id} className="ml-5 mt-1">
                  <p className="flex items-center gap-1.5"><Building2 size={13} className="text-slate-500" />{r.rif} — {r.client_name}</p>
                  {r.stores.map(s => (
                    <p key={s.quote_id} className="ml-5 text-xs text-slate-600 flex items-center gap-1.5"><Store size={12} />{s.store_name} · {s.equipments.length} equipo(s)</p>
                  ))}
                </div>
              ))}
            </div>
          ))}
        </div>
      ))}
    </div>
  );
};

export const EquipmentByRif = ({ rifs, testId = 'mp-equipment' }) => (
  <div className="space-y-3 text-sm" data-testid={testId}>
    {rifs.map(r => (
      <div key={r.client_id} className="border border-slate-200 rounded-lg p-3" data-testid={`${testId}-rif-${r.client_id}`}>
        <p className="font-semibold flex items-center gap-1.5"><Building2 size={14} className="text-slate-600" />RIF: {r.rif} — {r.client_name}
          <span className="text-xs font-normal text-slate-500">({r.equipment_count} equipo{r.equipment_count === 1 ? '' : 's'})</span></p>
        {r.stores.map(s => (
          <div key={s.quote_id} className="ml-4 mt-2">
            <p className="text-xs font-medium text-slate-700">• {s.store_name}</p>
            {s.equipments.length === 0 ? <p className="ml-4 text-[11px] text-slate-400">Sin equipos asignados en Almacén</p> : s.equipments.map(e => (
              <p key={e.serial} className="ml-4 text-[11px] font-mono text-slate-600"><Cpu size={10} className="inline mr-1" />{e.modelo} | Serial: {e.serial} | Origen: {e.origen}</p>
            ))}
          </div>
        ))}
      </div>
    ))}
  </div>
);

export const QuoteSummaries = ({ summaries, testId = 'mp-summaries' }) => (
  <div className="space-y-3 text-sm" data-testid={testId}>
    {(summaries || []).map(q => {
      const pg = (q.pg_setup_items || []).filter(i => (i.banco || '').trim() && (i.banco || '').toUpperCase() !== 'N/A');
      return (
        <div key={q.quote_id} className="border border-slate-200 rounded-lg overflow-hidden" data-testid={`${testId}-${q.quote_id}`}>
          <div className="bg-slate-50 px-3 py-2 flex flex-wrap items-center gap-x-3 text-xs">
            <span className="font-mono font-semibold text-slate-800">{q.quote_number}</span>
            <span className="text-slate-600">{q.client?.rif} — {q.client_name}</span>
            <span className="text-slate-500">{q.store_name}</span>
            <span className="ml-auto text-slate-500">Cajas: <b>{q.box_count}</b> · Bancos: <b>{(q.banks || []).length}</b></span>
          </div>
          <table className="w-full text-xs">
            <thead className="text-[10px] uppercase text-slate-400"><tr><th className="text-left px-3 py-1">Banco</th><th className="text-left">Medio de pago / Concepto</th><th className="text-right px-3">Cajas</th></tr></thead>
            <tbody>
              {pg.length ? pg.map((i, k) => (
                <tr key={k} className="border-t border-slate-100"><td className="px-3 py-1">{i.banco}</td><td>{i.concepto}</td><td className="text-right px-3">—</td></tr>
              )) : (q.services || []).map((i, k) => (
                <tr key={k} className="border-t border-slate-100"><td className="px-3 py-1">{i.bank_name}</td><td>{i.item_name}</td><td className="text-right px-3">{i.quantity ?? q.box_count}</td></tr>
              ))}
              {!pg.length && !(q.services || []).length && <tr><td colSpan={3} className="px-3 py-2 text-slate-400">Sin bancos/productos</td></tr>}
            </tbody>
          </table>
        </div>
      );
    })}
  </div>
);

export default function Multiprojects() {
  const navigate = useNavigate();
  const [level, setLevel] = useState('grupo');
  const [entities, setEntities] = useState([]);
  const [entityQ, setEntityQ] = useState('');
  const [entity, setEntity] = useState(null);
  const [quotes, setQuotes] = useState(null);
  const [sel, setSel] = useState([]);
  const [searching, setSearching] = useState(false);
  const [step, setStep] = useState(0);
  const [preview, setPreview] = useState(null);
  const [instructions, setInstructions] = useState('');
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    setEntity(null); setEntityQ(''); setQuotes(null); setSel([]);
    api.get('/multiprojects/entities', { params: { level } }).then(r => setEntities(r.data.items || [])).catch(() => setEntities([]));
  }, [level]);

  const options = useMemo(() => entities.filter(e => e.label.toLowerCase().includes(entityQ.toLowerCase())).slice(0, 30), [entities, entityQ]);
  const search = async () => {
    setSearching(true); setSel([]);
    try { const r = await api.get('/multiprojects/search', { params: { level, value: entity.value } }); setQuotes(r.data.quotes); }
    catch (e) { toast.error(e.response?.data?.detail || 'Error en la búsqueda'); }
    finally { setSearching(false); }
  };
  const toggle = (id) => setSel(p => (p.includes(id) ? p.filter(x => x !== id) : [...p, id]));
  const totalEq = (quotes || []).filter(q => sel.includes(q.quote_id)).reduce((a, q) => a + q.equipment_count, 0);

  const start = async () => {
    try { const r = await api.post('/multiprojects/preview', { quote_ids: sel }); setPreview(r.data); setStep(1); }
    catch (e) { toast.error(e.response?.data?.detail || 'No se pudo consolidar'); }
  };
  const create = async () => {
    setCreating(true);
    try {
      const r = await api.post('/multiprojects/create', { quote_ids: sel, implementation_instructions: instructions || null });
      toast.success(`Proyecto ${r.data.project_number} creado con ${r.data.quotes.length} cotizaciones`);
      setStep(0); navigate(`/projects/${r.data.project_id}`);
    } catch (e) { toast.error(e.response?.data?.detail || 'Error al crear el proyecto'); }
    finally { setCreating(false); }
  };

  const STEPS = ['Estructura jerárquica', 'Equipos por RIF', 'Confirmar'];
  return (
    <div className="flex min-h-screen bg-slate-50">
      <Sidebar />
      <main className="flex-1 p-6 lg:p-8 overflow-x-hidden" data-testid="multiprojects-page">
        <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2"><Link2 className="text-indigo-600" />Multiproyectos</h1>
        <p className="text-sm text-slate-500 mt-1">Consolida 2 o más cotizaciones activas en un único proyecto de implementación.</p>

        <section className="bg-white border border-slate-200 rounded-xl p-5 mt-6">
          <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">1. Criterio de búsqueda</p>
          <div className="flex flex-wrap gap-2 mb-3">
            {LEVELS.map(l => (
              <button key={l.id} onClick={() => setLevel(l.id)} data-testid={`mp-level-${l.id}`}
                className={`px-3 py-1.5 rounded-full text-sm border transition-colors ${level === l.id ? 'bg-indigo-600 text-white border-indigo-600' : 'bg-white text-slate-600 border-slate-300 hover:border-indigo-400'}`}>{l.label}</button>
            ))}
          </div>
          <div className="flex gap-2 items-start">
            <div className="relative flex-1 max-w-xl">
              <Search size={14} className="absolute left-2.5 top-2.5 text-slate-400" />
              <Input value={entity ? entity.label : entityQ} onChange={e => { setEntity(null); setEntityQ(e.target.value); }}
                placeholder={`Buscar ${LEVELS.find(l => l.id === level).label}...`} className="pl-8" data-testid="mp-entity-input" />
              {!entity && entityQ && (
                <div className="absolute z-20 mt-1 w-full bg-white border border-slate-200 rounded-md shadow-lg max-h-60 overflow-y-auto">
                  {options.map(o => (
                    <button key={o.value} onClick={() => setEntity(o)} className="block w-full text-left px-3 py-1.5 text-sm hover:bg-indigo-50"
                      data-testid={`mp-entity-option-${o.value}`}>{o.label}</button>
                  ))}
                  {options.length === 0 && <p className="px-3 py-2 text-xs text-slate-400">Sin coincidencias</p>}
                </div>
              )}
            </div>
            <Button onClick={search} disabled={!entity || searching} className="bg-indigo-600 hover:bg-indigo-700 text-white" data-testid="mp-search-btn">
              {searching ? <Loader2 size={14} className="mr-1 animate-spin" /> : <Search size={14} className="mr-1" />}Buscar activas
            </Button>
          </div>
        </section>

        {quotes && (
          <section className="bg-white border border-slate-200 rounded-xl p-5 mt-4">
            <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">2. Cotizaciones activas elegibles ({quotes.length})</p>
            {quotes.length === 0 ? <p className="text-sm text-slate-400" data-testid="mp-empty">No hay cotizaciones activas elegibles para este criterio.</p> : (
              <table className="w-full text-sm">
                <thead className="text-[11px] uppercase text-slate-400 border-b"><tr>
                  <th className="w-8" /><th className="text-left py-2">Nro Cotización</th><th className="text-left">Cliente (RIF / Sucursal)</th>
                  <th className="text-left">Tipo</th><th className="text-left">Estatus</th><th className="text-right">Equipos Alm.</th></tr></thead>
                <tbody>
                  {quotes.map(q => (
                    <tr key={q.quote_id} className={`border-b border-slate-100 ${sel.includes(q.quote_id) ? 'bg-indigo-50/60' : ''}`} data-testid={`mp-row-${q.quote_id}`}>
                      <td><input type="checkbox" checked={sel.includes(q.quote_id)} onChange={() => toggle(q.quote_id)} data-testid={`mp-check-${q.quote_id}`} /></td>
                      <td className="py-2 font-mono text-xs">{q.quote_number}</td>
                      <td><span title={q.fantasy_name}>{q.client_name}</span> <span className="text-xs text-slate-400">{q.rif} · {q.store_name}</span></td>
                      <td className="text-xs">{q.quote_type}</td><td className="text-xs">{q.quote_status}</td>
                      <td className="text-right text-xs">{q.equipment_count ? `${q.equipment_count} asig.` : '0'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
            <div className="flex items-center justify-between mt-4">
              <p className="text-sm text-slate-600" data-testid="mp-selection-summary">Seleccionadas: <b>{sel.length}</b> | Total consolidado: <b>{totalEq}</b> equipos</p>
              <Button onClick={start} disabled={sel.length < 2} className="bg-emerald-600 hover:bg-emerald-700 text-white" data-testid="mp-send-btn">
                <Rocket size={15} className="mr-1.5" />Enviar a Implementación ({sel.length} cotiz.)
              </Button>
            </div>
          </section>
        )}

        <Dialog open={step > 0} onOpenChange={(o) => !o && !creating && setStep(0)}>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto" data-testid="mp-dialog">
            <DialogHeader>
              <DialogTitle>Paso {step} de 3: {STEPS[step - 1]}</DialogTitle>
              <div className="flex gap-1 mt-2">{STEPS.map((s, i) => <div key={s} className={`h-1 flex-1 rounded ${i < step ? 'bg-indigo-600' : 'bg-slate-200'}`} />)}</div>
            </DialogHeader>
            {preview && step === 1 && <><HierarchyStep preview={preview} />
              <p className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mt-3">Resumen ejecutivo por cotización</p>
              <QuoteSummaries summaries={preview.summaries} /></>}
            {preview && step === 2 && <EquipmentByRif rifs={preview.rifs} />}
            {preview && step === 3 && (
              <div className="space-y-3 text-sm" data-testid="mp-confirm">
                <p>Se creará <b>un único proyecto {preview.level}</b> con {sel.length} cotizaciones, {preview.rifs.length} RIF(s) y {preview.total_equipments} equipo(s) asignados.</p>
                <p className="text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded p-2">Todas las cotizaciones quedarán marcadas como <b>Enviadas a Implementación</b> y pasarán al <b>Histórico</b> con el comentario de Multiproyecto.</p>
                <Textarea rows={3} value={instructions} onChange={e => setInstructions(e.target.value)} placeholder="Instrucciones adicionales para Implementación (opcional)" data-testid="mp-instructions" />
              </div>
            )}
            <DialogFooter>
              <Button variant="outline" disabled={creating} onClick={() => (step === 1 ? setStep(0) : setStep(step - 1))} data-testid="mp-back-btn">{step === 1 ? 'Cancelar' : 'Atrás'}</Button>
              {step < 3 ? (
                <Button onClick={() => setStep(step + 1)} className="bg-indigo-600 hover:bg-indigo-700 text-white" data-testid="mp-next-btn">Siguiente paso <ChevronRight size={14} className="ml-1" /></Button>
              ) : (
                <Button onClick={create} disabled={creating} className="bg-emerald-600 hover:bg-emerald-700 text-white" data-testid="mp-create-btn">
                  {creating && <Loader2 size={14} className="mr-1 animate-spin" />}Crear Proyecto consolidado
                </Button>
              )}
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </main>
    </div>
  );
}
