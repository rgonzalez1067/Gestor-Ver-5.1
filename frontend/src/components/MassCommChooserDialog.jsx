import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './ui/dialog';
import { Users, Landmark, ChevronRight } from 'lucide-react';

const Option = ({ icon: Icon, title, desc, onClick, testid, tone }) => (
  <button
    type="button"
    onClick={onClick}
    data-testid={testid}
    className={`group w-full text-left flex items-center gap-4 p-4 rounded-xl border transition-colors ${tone}`}
  >
    <span className="p-3 rounded-lg bg-white shadow-sm"><Icon size={22} /></span>
    <span className="flex-1">
      <span className="block font-semibold text-slate-800">{title}</span>
      <span className="block text-xs text-slate-500 mt-0.5">{desc}</span>
    </span>
    <ChevronRight size={18} className="text-slate-400 group-hover:translate-x-0.5 transition-transform" />
  </button>
);

export const MassCommChooserDialog = ({ open, onOpenChange, onPick }) => (
  <Dialog open={open} onOpenChange={onOpenChange}>
    <DialogContent className="max-w-md" data-testid="mass-comm-chooser">
      <DialogHeader>
        <DialogTitle className="text-blue-700">Comunicación Masiva</DialogTitle>
        <DialogDescription className="text-xs text-slate-500">Seleccione el canal de despacho.</DialogDescription>
      </DialogHeader>
      <div className="space-y-3">
        <Option icon={Users} title="A Integradores" desc="Envío masivo a los integradores registrados"
          onClick={() => onPick('integrators')} testid="mass-chooser-integrators"
          tone="border-blue-200 hover:bg-blue-50 text-blue-700" />
        <Option icon={Landmark} title="A Bancos/Entes" desc="Envío a contactos de instituciones financieras"
          onClick={() => onPick('banks')} testid="mass-chooser-banks"
          tone="border-emerald-200 hover:bg-emerald-50 text-emerald-700" />
      </div>
    </DialogContent>
  </Dialog>
);

export default MassCommChooserDialog;
