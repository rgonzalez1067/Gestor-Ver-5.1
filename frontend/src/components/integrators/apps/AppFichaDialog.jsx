import { useCallback, useEffect, useState } from 'react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../ui/tabs';
import { Lock, ShieldCheck, AlertTriangle } from 'lucide-react';
import { AppDataTab } from './AppDataTab';
import { AppMatrixTab } from './AppMatrixTab';
import { AppContactsTab } from './AppContactsTab';
import { AppCertificatesTab } from './AppCertificatesTab';
import { isActiveApp, isLockedApp } from './appPayload';
import api from '../../../utils/api';
import { toast } from 'sonner';

const LockBanner = ({ locked, canModifyLocked }) => {
  if (!locked) return null;
  return canModifyLocked ? (
    <div className="rounded-md bg-blue-50 border border-blue-200 text-blue-800 text-xs px-3 py-2 flex items-center gap-2" data-testid="app-lock-banner-special">
      <ShieldCheck size={14} />Aplicativo certificado. Tienes la Función Especial: puedes modificar la matriz y los datos técnicos indicando el motivo.
    </div>
  ) : (
    <div className="rounded-md bg-slate-100 border border-slate-200 text-slate-600 text-xs px-3 py-2 flex items-center gap-2" data-testid="app-lock-banner">
      <Lock size={14} />Aplicativo certificado en solo lectura. Para modificarlo se requiere la Función Especial «Modificar Aplicativos Certificados».
    </div>
  );
};

export const AppFichaDialog = ({ integratorId, onClose, canEdit, canModifyLocked, canManageCerts, onChanged }) => {
  const [app, setApp] = useState(null);
  const [products, setProducts] = useState([]);

  const load = useCallback(async () => {
    try { setApp((await api.get(`/integrators/${integratorId}`)).data); }
    catch { toast.error('No se pudo cargar el aplicativo'); }
  }, [integratorId]);
  useEffect(() => { if (integratorId) { setApp(null); load(); } }, [integratorId, load]);
  useEffect(() => { api.get('/integrators/products').then((r) => setProducts(r.data || [])).catch(() => {}); }, []);

  const locked = isLockedApp(app);
  const matrixLocked = !isActiveApp(app);
  const refresh = () => { load(); onChanged?.(); };

  return (
    <Dialog open={!!integratorId} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto" data-testid="app-ficha-dialog">
        <DialogHeader>
          <DialogTitle className="font-manrope text-xl flex items-center gap-2 flex-wrap">
            Ficha del Aplicativo · <span data-testid="app-ficha-title">{app?.app_name || '...'}</span>
            {app?.integrator_status && <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700 font-semibold" data-testid="app-ficha-status">{app.integrator_status}</span>}
            {app?.cert_outdated && <span className="text-xs px-2 py-0.5 rounded-full bg-amber-100 text-amber-700 font-semibold inline-flex items-center gap-1" data-testid="app-ficha-outdated"><AlertTriangle size={11} />Certificado desactualizado</span>}
          </DialogTitle>
          <p className="text-xs text-slate-500">{app?.name}</p>
        </DialogHeader>
        {!app ? <p className="text-sm text-slate-400 py-8 text-center">Cargando...</p> : (
          <div className="space-y-3">
            <LockBanner locked={locked || matrixLocked} canModifyLocked={canModifyLocked} />
            <Tabs defaultValue="data">
              <TabsList data-testid="app-ficha-tabs">
                <TabsTrigger value="data" data-testid="app-tab-data">Datos Técnicos</TabsTrigger>
                <TabsTrigger value="matrix" data-testid="app-tab-matrix">Matriz de Productos</TabsTrigger>
                <TabsTrigger value="contacts" data-testid="app-tab-contacts">Contactos Técnicos</TabsTrigger>
                <TabsTrigger value="certs" data-testid="app-tab-certs">Certificados</TabsTrigger>
              </TabsList>
              <TabsContent value="data" className="pt-3"><AppDataTab app={app} locked={locked} editable={locked ? canModifyLocked : canEdit} onSaved={refresh} /></TabsContent>
              <TabsContent value="matrix" className="pt-3"><AppMatrixTab app={app} products={products} locked={matrixLocked} editable={matrixLocked ? canModifyLocked : canEdit} onSaved={refresh} /></TabsContent>
              <TabsContent value="contacts" className="pt-3"><AppContactsTab app={app} /></TabsContent>
              <TabsContent value="certs" className="pt-3"><AppCertificatesTab app={app} canManage={canManageCerts} onChanged={refresh} /></TabsContent>
            </Tabs>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
};
