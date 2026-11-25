import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from '../ui/alert-dialog';
import { AlertTriangle } from 'lucide-react';

export const PENDING_CERT_TEXT = 'Pendiente por certificación del Integrador';

export const pendLabel = (item) => (item.pendiente_certificacion ? `${item.medio_pago_name} — (${PENDING_CERT_TEXT})` : item.medio_pago_name);

const norm = (v) => (v || '').trim().toLowerCase();

// Medios de pago vinculados a un Producto de Integración que NO está en 'C' para el aplicativo elegido.
export const findUncertified = (names, integratorId, integrators, links) => {
  const app = integrators.find((i) => i.integrator_id === integratorId);
  if (!app || !links.length) return [];
  const certs = app.certifications || {};
  return names.flatMap((name) => {
    const link = links.find((l) => norm(l.medio_pago_name) === norm(name));
    if (!link || String(certs[link.producto_id] || '').trim().toUpperCase() === 'C') return [];
    return [{ medio: name, producto: link.nombre }];
  });
};

export const PendingCertBadge = ({ testId }) => (
  <span className="px-1.5 py-0.5 text-[11px] font-medium bg-amber-100 text-amber-800 border border-amber-200 rounded" data-testid={testId}>{PENDING_CERT_TEXT}</span>
);

export const CertWarningDialog = ({ warn, onCancel, onAccept }) => (
  <AlertDialog open={!!warn}>
    <AlertDialogContent className="max-w-xl" onEscapeKeyDown={onCancel} data-testid="cert-warning-dialog">
      <AlertDialogHeader>
        <AlertDialogTitle className="flex items-center gap-2 text-amber-700"><AlertTriangle size={20} />Advertencia: producto no certificado con el aplicativo</AlertDialogTitle>
        <AlertDialogDescription asChild>
          <div className="space-y-3 text-sm text-slate-700">
            {warn?.flagged.map((f) => (
              <p key={f.medio}>El Medio de Pago <b>«{f.medio}»</b> está asociado al producto <b>«{f.producto}»</b>, el cual NO se encuentra certificado actualmente para el aplicativo:</p>
            ))}
            <ul className="list-disc pl-5">
              <li>Integrador: <b>{warn?.integrator?.name || '—'}</b></li>
              <li>Aplicativo: <b>{warn?.integrator?.app_name || '—'}</b></li>
            </ul>
            <p>¿Desea incluir {warn?.flagged.length > 1 ? 'estos Medios de Pago' : 'este Medio de Pago'} en la cotización bajo condición de certificación pendiente?</p>
          </div>
        </AlertDialogDescription>
      </AlertDialogHeader>
      <AlertDialogFooter>
        <AlertDialogCancel onClick={onCancel} data-testid="cert-warning-cancel">Cancelar / No Agregar</AlertDialogCancel>
        <AlertDialogAction onClick={onAccept} className="bg-amber-600 hover:bg-amber-700" data-testid="cert-warning-accept">Sí, Agregar como Pendiente</AlertDialogAction>
      </AlertDialogFooter>
    </AlertDialogContent>
  </AlertDialog>
);
