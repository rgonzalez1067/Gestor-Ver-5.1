import { useState, useEffect, useRef } from 'react';
import { Label } from './ui/label';
import { RichTextEditor } from './RichTextEditor';

export const PROJECT_FEATURES_LABEL = 'Características particulares del Proyecto';
const DEBOUNCE_MS = 400;

// Texto enriquecido (máx. 1.000 caracteres) que genera una página propia en el PDF de la cotización,
// antes de las condiciones generales. El texto se mantiene local y se propaga al padre con debounce
// para no re-renderizar todo el formulario en cada tecla.
export const ProjectFeaturesField = ({ value, onChange, testid = 'project-features-editor', className = '' }) => {
  const [local, setLocal] = useState(value || '');
  const lastSent = useRef(value || '');
  const timer = useRef(null);
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;
  const pending = useRef(value || '');

  useEffect(() => {
    if ((value || '') !== lastSent.current) {
      lastSent.current = value || '';
      setLocal(value || '');
    }
  }, [value]);

  const flush = (html) => {
    clearTimeout(timer.current);
    timer.current = null;
    if (html !== lastSent.current) {
      lastSent.current = html;
      onChangeRef.current(html);
    }
  };

  useEffect(() => () => { if (timer.current) flush(pending.current); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleChange = (html, len) => {
    const next = len === 0 ? '' : html;
    setLocal(next);
    pending.current = next;
    clearTimeout(timer.current);
    timer.current = setTimeout(() => flush(next), DEBOUNCE_MS);
  };

  return (
    <div className={className} data-testid={`${testid}-wrapper`} onBlur={() => timer.current && flush(pending.current)}>
      <Label className="text-sm font-medium text-slate-700">{PROJECT_FEATURES_LABEL}</Label>
      <p className="text-[11px] text-slate-400 mb-1.5">
        Si se completa, el PDF incluirá una página con este título antes de las condiciones generales.
      </p>
      <RichTextEditor
        value={local}
        onChange={handleChange}
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
};

export default ProjectFeaturesField;
