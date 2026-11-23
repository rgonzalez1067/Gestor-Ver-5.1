import { Users, UserCheck, XCircle, Clock, TrendingUp, MessageSquare } from 'lucide-react';

const CARDS = [
  ['total', 'Total Contactos', Users, 'text-slate-800 bg-slate-50'],
  ['convertidos', 'Convertidos', UserCheck, 'text-emerald-700 bg-emerald-50'],
  ['cerrados', 'Cerrados', XCircle, 'text-blue-700 bg-blue-50'],
  ['en_gestion', 'En Gestión', Clock, 'text-amber-700 bg-amber-50'],
  ['tasa_conversion', 'Tasa de Conversión', TrendingUp, 'text-emerald-700 bg-emerald-50', '%'],
  ['interacciones', 'Interacciones', MessageSquare, 'text-violet-700 bg-violet-50'],
];

export const AnalysisKpis = ({ kpis }) => (
  <div className="grid grid-cols-3 lg:grid-cols-6 gap-2" data-testid="analysis-kpis">
    {CARDS.map(([k, label, Icon, cls, suffix]) => (
      <div key={k} className={`rounded-lg border border-slate-200 px-3 py-2 ${cls}`} data-testid={`analysis-kpi-${k}`}>
        <p className="text-[10px] uppercase tracking-wide font-semibold opacity-80 flex items-center gap-1"><Icon size={11} />{label}</p>
        <p className="text-xl font-bold leading-tight">{kpis?.[k] ?? 0}{suffix || ''}</p>
      </div>
    ))}
  </div>
);
