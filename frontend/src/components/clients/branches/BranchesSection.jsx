import { useState } from 'react';
import { toast } from 'sonner';
import api from '../../../utils/api';
import { Button } from '../../ui/button';
import { Plus, Pencil, Trash2, User, Link2 } from 'lucide-react';
import { BranchFormDialog } from './BranchFormDialog';

const ownContacts = (b) => (b.contacts || []).filter(c => (c.full_name || c.email || '').trim());

const ContactsBadge = ({ b }) => {
  const n = ownContacts(b).length;
  return n ? (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-violet-50 text-violet-700 border border-violet-200" data-testid={`branch-contacts-own-${b.client_id}`}><User size={11} /> Propios ({n})</span>
  ) : (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-sky-50 text-sky-700 border border-sky-200" data-testid={`branch-contacts-inherited-${b.client_id}`}><Link2 size={11} /> Heredados RIF</span>
  );
};

// Pestaña "Sucursales" de la Ficha de Razón Social (RIF Principal).
export const BranchesSection = ({ principal, branches, principalContacts, canEdit, onChanged }) => {
  const [dialog, setDialog] = useState({ open: false, branch: null });
  const remove = async (b) => {
    if (!window.confirm(`¿Eliminar la sucursal "${b.sucursal}"?`)) return;
    try {
      await api.delete(`/clients/${b.client_id}`);
      toast.success('Sucursal eliminada');
      onChanged?.();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'No se pudo eliminar la sucursal');
    }
  };
  const sorted = [...branches].sort((a, b) => (a.sucursal || '').localeCompare(b.sucursal || '', 'es'));
  const totalCajas = sorted.reduce((s, b) => s + (parseInt(b.cantidad_cajas, 10) || 0), 0);

  return (
    <div className="space-y-3" data-testid="branches-section">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm font-semibold text-slate-800">Sucursales / Tiendas registradas bajo este RIF</p>
          <p className="text-xs text-slate-500">{sorted.length} sucursal(es) · {totalCajas} cajas · todas comparten el RIF {principal.rif}</p>
        </div>
        {canEdit && <Button type="button" size="sm" onClick={() => setDialog({ open: true, branch: null })} className="bg-amber-600 hover:bg-amber-700" data-testid="branches-add-btn"><Plus size={14} className="mr-1" />Agregar Sucursal</Button>}
      </div>
      <div className="border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-slate-50 text-xs uppercase text-slate-600">
            <tr><th className="px-3 py-2 text-left">Nombre de Sucursal</th><th className="px-3 py-2 text-left">Dirección Física</th>
              <th className="px-3 py-2 text-center w-20">Cajas</th><th className="px-3 py-2 text-left w-36">Contactos</th>{canEdit && <th className="w-20" />}</tr>
          </thead>
          <tbody className="divide-y">
            {sorted.length === 0 && <tr><td colSpan={5} className="px-3 py-6 text-center text-slate-400" data-testid="branches-empty">Este RIF aún no tiene sucursales registradas.</td></tr>}
            {sorted.map(b => (
              <tr key={b.client_id} className="hover:bg-slate-50" data-testid={`branch-row-${b.client_id}`}>
                <td className="px-3 py-2 font-medium text-slate-800">{b.sucursal}</td>
                <td className="px-3 py-2 text-slate-600">{b.branch_address || <span className="text-slate-400">—</span>}</td>
                <td className="px-3 py-2 text-center font-semibold" data-testid={`branch-cajas-${b.client_id}`}>{b.cantidad_cajas ?? '—'}</td>
                <td className="px-3 py-2"><ContactsBadge b={b} /></td>
                {canEdit && (
                  <td className="px-2 py-2 text-right whitespace-nowrap">
                    <button type="button" onClick={() => setDialog({ open: true, branch: b })} className="p-1 text-slate-500 hover:text-blue-600" data-testid={`branch-edit-${b.client_id}`}><Pencil size={14} /></button>
                    <button type="button" onClick={() => remove(b)} className="p-1 text-slate-500 hover:text-red-600" data-testid={`branch-delete-${b.client_id}`}><Trash2 size={14} /></button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <BranchFormDialog open={dialog.open} onOpenChange={(o) => setDialog(d => ({ ...d, open: o }))} principal={principal}
        branch={dialog.branch} principalContacts={principalContacts} onSaved={onChanged} />
    </div>
  );
};
