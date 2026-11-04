import { useNavigate } from 'react-router-dom';
import { ArrowLeft, FileCode } from 'lucide-react';
import { Sidebar } from '../components/Sidebar';
import { Button } from '../components/ui/button';
import { EmailTemplatesEditor } from '../components/EmailTemplatesEditor';

export default function EmailTemplatesPage() {
  const navigate = useNavigate();
  return (
    <div className="flex min-h-screen bg-slate-50">
      <Sidebar />
      <main className="flex-1 p-8" data-testid="email-templates-page">
        <div className="max-w-6xl mx-auto">
          <Button variant="ghost" size="sm" onClick={() => navigate('/settings')} className="mb-4 -ml-3" data-testid="back-to-settings">
            <ArrowLeft size={16} className="mr-2" /> Volver a Configuración
          </Button>
          <div className="flex items-start gap-3 mb-6">
            <div className="w-12 h-12 rounded-xl bg-blue-100 text-blue-600 flex items-center justify-center flex-shrink-0">
              <FileCode size={26} />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-900 font-manrope">Plantillas de Correo Electrónico</h1>
              <p className="text-sm text-slate-600 mt-0.5 max-w-3xl">
                Personalice el contenido de los correos automáticos que envía el sistema en cada etapa del flujo de trabajo.
                Cada sede tiene sus propias plantillas para mantener la identidad y control separado.
              </p>
            </div>
          </div>
          <div className="bg-white rounded-xl border border-slate-200 p-6">
            <EmailTemplatesEditor />
          </div>
        </div>
      </main>
    </div>
  );
}
