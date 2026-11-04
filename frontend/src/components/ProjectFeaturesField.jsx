import { Label } from './ui/label';
import { RichTextEditor } from './RichTextEditor';

export const PROJECT_FEATURES_LABEL = 'Características particulares del Proyecto';

// Texto enriquecido (máx. 1.000 caracteres) que genera una página propia en el PDF de la cotización,
// antes de las condiciones generales.
export const ProjectFeaturesField = ({ value, onChange, testid = 'project-features-editor', className = '' }) => (
  <div className={className} data-testid={`${testid}-wrapper`}>
    <Label className="text-sm font-medium text-slate-700">{PROJECT_FEATURES_LABEL}</Label>
    <p className="text-[11px] text-slate-400 mb-1.5">
      Si se completa, el PDF incluirá una página con este título antes de las condiciones generales.
    </p>
    <RichTextEditor
      value={value || ''}
      onChange={(html, len) => onChange(len === 0 ? '' : html)}
      maxChars={1000}
      minHeight={240}
      maxHeight={420}
      enableImagePaste={false}
      enableHeadings
      showTableControls={false}
      placeholder="Describa las características particulares del proyecto..."
      testid={testid}
    />
  </div>
);

export default ProjectFeaturesField;
