import { useState, useEffect } from 'react';
import { ChevronRight, ChevronDown, Tag, FileText, MapPin, Loader2, Store } from 'lucide-react';
import api from '../../../utils/api';

const useLazy = (url, open) => {
  const [data, setData] = useState(null);
  useEffect(() => {
    if (!open || data) return;
    api.get(url).then(r => setData(r.data)).catch(() => setData([]));
  }, [open, url, data]);
  return data;
};

const Toggle = ({ open, onClick, children, testId, className = '' }) => (
  <button type="button" onClick={onClick} data-testid={testId} aria-expanded={open}
    className={`w-full flex items-center gap-2 px-2 py-1.5 rounded-md text-left text-sm transition-colors hover:bg-slate-100 ${className}`}>
    {open ? <ChevronDown size={14} className="text-slate-400 shrink-0" /> : <ChevronRight size={14} className="text-slate-400 shrink-0" />}
    {children}
  </button>
);

const Loading = () => <div className="flex items-center gap-2 text-xs text-slate-400 px-2 py-1"><Loader2 size={12} className="animate-spin" /> Cargando...</div>;
const Empty = ({ text, testId }) => <p className="text-xs text-slate-400 italic px-2 py-1" data-testid={testId}>{text}</p>;

const BranchList = ({ clientId }) => {
  const data = useLazy(`/clients/${clientId}/branches`, true);
  if (!data) return <Loading />;
  const branches = data.branches || [];
  return (
    <ul className="ml-5 border-l border-amber-200 pl-3 space-y-0.5" data-testid={`tree-branches-${clientId}`}>
      <li className="flex items-center gap-2 text-xs text-slate-500 py-1"><Store size={12} className="text-indigo-500" /> Sede Principal</li>
      {branches.length === 0 && <Empty text="Sin sucursales adscritas." testId={`tree-no-branches-${clientId}`} />}
      {branches.map(b => (
        <li key={b.client_id} className="flex items-center gap-2 text-sm text-slate-700 py-1" data-testid={`tree-branch-${b.client_id}`}>
          <MapPin size={12} className="text-amber-500 shrink-0" />
          <span className="font-medium">{b.sucursal}</span>
          {b.condicion && <span className="text-[10px] text-slate-400">· {b.condicion}</span>}
        </li>
      ))}
    </ul>
  );
};

const RifNode = ({ rif }) => {
  const [open, setOpen] = useState(false);
  return (
    <li data-testid={`tree-rif-node-${rif.client_id}`}>
      <Toggle open={open} onClick={() => setOpen(o => !o)} testId={`tree-rif-${rif.client_id}`}>
        <FileText size={13} className="text-indigo-500 shrink-0" />
        <span className="font-mono text-xs text-slate-500">{rif.rif}</span>
        <span className="font-medium text-slate-800 truncate">{rif.legal_name}</span>
        <span className="ml-auto text-[10px] text-amber-700 bg-amber-50 px-1.5 rounded-full shrink-0">{rif.branches_count} suc.</span>
      </Toggle>
      {open && <BranchList clientId={rif.client_id} />}
    </li>
  );
};

export const RifList = ({ brandId }) => {
  const rifs = useLazy(`/marcas/${brandId}/rifs`, true);
  if (!rifs) return <Loading />;
  return (
    <ul className="ml-5 border-l border-indigo-200 pl-3 space-y-0.5" data-testid={`tree-rifs-${brandId}`}>
      {rifs.length === 0 && <Empty text="Sin RIFs asociados." testId={`tree-no-rifs-${brandId}`} />}
      {rifs.map(r => <RifNode key={r.client_id} rif={r} />)}
    </ul>
  );
};

export const BrandNode = ({ brand, defaultOpen = false }) => {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <li data-testid={`tree-brand-node-${brand.brand_id}`}>
      <Toggle open={open} onClick={() => setOpen(o => !o)} testId={`tree-brand-${brand.brand_id}`}>
        <Tag size={13} className="text-teal-600 shrink-0" />
        <span className="font-semibold text-slate-800 truncate">{brand.name}</span>
        <span className="ml-auto text-[10px] text-indigo-700 bg-indigo-50 px-1.5 rounded-full shrink-0">{brand.rif_count} RIF</span>
      </Toggle>
      {open && <RifList brandId={brand.brand_id} />}
    </li>
  );
};

export const GroupTree = ({ groupId }) => {
  const brands = useLazy(`/grupos-economicos/${groupId}/marcas`, true);
  if (!brands) return <Loading />;
  return (
    <ul className="space-y-0.5" data-testid={`tree-group-${groupId}`}>
      {brands.length === 0 && <Empty text="Este grupo no tiene marcas asociadas." testId={`tree-no-brands-${groupId}`} />}
      {brands.map(b => <BrandNode key={b.brand_id} brand={b} />)}
    </ul>
  );
};
