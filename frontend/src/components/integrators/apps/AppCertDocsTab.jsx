import { useEffect, useState } from 'react';
import { FolderOpen, FolderCheck } from 'lucide-react';
import api from '../../../utils/api';

export const AppCertDocsTab = ({ app }) => {
  const [data, setData] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    setData(null); setError(false);
    api.get(`/integrators/${app.integrator_id}/certification-documents`)
      .then((r) => setData(r.data)).catch(() => setError(true));
  }, [app.integrator_id]);

  if (error) return <p className="text-sm text-rose-600 py-6 text-center" data-testid="cert-docs-error">No se pudo cargar la carpeta de documentos.</p>;
  if (!data) return <p className="text-sm text-slate-400 py-6 text-center" data-testid="cert-docs-loading">Cargando carpeta...</p>;

  return (
    <div className="space-y-4" data-testid="cert-docs-tab">
      <div className="text-center">
        <p className="text-sm font-semibold text-slate-800 inline-flex items-center gap-2"><FolderOpen size={16} className="text-amber-500" />Documentos de la Certificación</p>
        <p className="text-xs text-slate-500">Carpeta Digital de Anexos y Evidencias Técnicas</p>
      </div>
      {data.documents.length === 0 && (
        <div className="rounded-lg border-2 border-dashed border-slate-200 bg-slate-50 px-6 py-10 text-center" data-testid="cert-docs-empty">
          <FolderCheck size={32} className="mx-auto text-amber-400 mb-2" />
          <p className="text-sm font-medium text-slate-700">Carpeta de Anexos inicializada</p>
          <p className="text-xs text-slate-500 mt-1 max-w-md mx-auto">Esta sección almacenará los documentos fusionados y evidencias generadas durante el proceso de certificación del aplicativo.</p>
        </div>
      )}
    </div>
  );
};
