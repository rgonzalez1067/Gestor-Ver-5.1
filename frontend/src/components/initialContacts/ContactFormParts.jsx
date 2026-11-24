import { DialogHeader, DialogTitle, DialogDescription } from '../ui/dialog';

const TONES = { green: 'bg-green-600', blue: 'bg-blue-600' };

export const ContactModalHeader = ({ icon: Icon, tone, title, subtitle }) => (
  <DialogHeader className="px-6 py-4 border-b border-slate-200 bg-gradient-to-r from-slate-50 to-white text-left space-y-0">
    <div className="flex items-center gap-3">
      <span className={`h-10 w-10 rounded-lg ${TONES[tone]} text-white flex items-center justify-center shadow-sm`}><Icon size={20} /></span>
      <div>
        <DialogTitle className="text-lg">{title}</DialogTitle>
        <DialogDescription className="text-xs text-slate-500">{subtitle}</DialogDescription>
      </div>
    </div>
  </DialogHeader>
);

export const FormSection = ({ title, children }) => (
  <section className="rounded-lg border border-slate-200 bg-slate-50/50 p-4">
    <p className="text-[11px] font-semibold text-blue-600 uppercase tracking-wider mb-3">{title}</p>
    {children}
  </section>
);
