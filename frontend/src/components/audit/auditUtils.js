export const ACTION_STYLES = {
  CREATE: 'bg-emerald-100 text-emerald-700',
  UPDATE: 'bg-amber-100 text-amber-700',
  DELETE: 'bg-red-100 text-red-700',
};

export const fmtDate = (iso) => {
  if (!iso) return '';
  const d = new Date(iso);
  return d.toLocaleString('es-VE', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' });
};

export const EMPTY_FILTERS = { date_from: '', date_to: '', modules: [], action: 'TODAS', user: '', registro: '', field: '' };

// datetime-local (hora local) -> ISO UTC para el backend
export const toParams = (f) => {
  const p = {};
  if (f.date_from) p.date_from = new Date(f.date_from).toISOString();
  if (f.date_to) p.date_to = new Date(f.date_to).toISOString();
  if (f.modules.length) p.modules = f.modules.join(',');
  if (f.action && f.action !== 'TODAS') p.action = f.action;
  ['user', 'registro', 'field'].forEach((k) => { if (f[k].trim()) p[k] = f[k].trim(); });
  return p;
};
