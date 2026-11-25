import { Label } from '../ui/label';
import { Switch } from '../ui/switch';
import { RichTextEditor } from '../RichTextEditor';

const ZoneEditor = ({ zone, label, value, onChange, editorRef, zoneRef, context }) => (
  <div data-testid={`fusion-zone-${zone}`}>
    <Label className="text-xs">{label}</Label>
    <div onMouseDown={() => { zoneRef.current = zone; }}>
      <RichTextEditor ref={editorRef} value={value} onChange={(html) => { zoneRef.current = zone; onChange(html); }}
        maxChars={5000} hardLimit={false} placeholder={`Contenido del ${label.toLowerCase()} (texto, variables o logo)...`}
        testid={`fusion-${zone}-editor-${context}`} minHeight={70} maxHeight={160} />
    </div>
  </div>
);

const CoverToggle = ({ id, label, checked, onChange }) => (
  <label className="flex items-center gap-2 text-xs text-slate-700 cursor-pointer">
    <Switch checked={checked} onCheckedChange={onChange} data-testid={id} />{label}
  </label>
);

export const FusionHeaderZone = (p) => <ZoneEditor zone="header" label="Encabezado" value={p.form.header_html} onChange={(h) => p.setForm(f => ({ ...f, header_html: h }))} {...p} />;

export const FusionFooterZone = (p) => <ZoneEditor zone="footer" label="Pie de Página" value={p.form.footer_html} onChange={(h) => p.setForm(f => ({ ...f, footer_html: h }))} {...p} />;

export const FusionCoverOptions = ({ form, setForm }) => (
  <div className="rounded-lg border border-amber-200 bg-amber-50/60 p-3" data-testid="fusion-cover-options">
    <p className="text-xs font-semibold text-amber-900 mb-2">Portada (página 1 del documento)</p>
    <div className="flex flex-wrap gap-6">
      <CoverToggle id="fusion-cover-header" label="La portada lleva Encabezado" checked={form.portada_encabezado} onChange={(v) => setForm(f => ({ ...f, portada_encabezado: v }))} />
      <CoverToggle id="fusion-cover-footer" label="La portada lleva Pie de Página" checked={form.portada_pie} onChange={(v) => setForm(f => ({ ...f, portada_pie: v }))} />
    </div>
  </div>
);
