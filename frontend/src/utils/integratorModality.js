// Filtrado dinámico de Integradores según Tipo de Proyecto.
// Regla de negocio basada en el "Tipo de Integración" del integrador
// (campo `integration_type`): CR / MP / PG / LP / TK. Centralizado para
// garantizar consistencia entre Cotizaciones y Proyectos Directos.
//
//   VPOS / VPOS Multi-RIF        → CR
//   MPOS / MPOS (Imple + POS)    → MP
//   Payment Gateway              → PG
//   Link de Pago / Tokenizador   → LP, TK   (opción combinada)

const _norm = (s) => (s || '').toString().trim().toUpperCase();

// Tipo de Proyecto → tipos de integración permitidos.
const PROJECT_TYPE_INTEGRATION = {
  VPOS: ['CR'],
  VPOS_MULTIRIF: ['CR'],
  MPOS: ['MP'],
  FAST_TRACK: ['MP'],
  GATEWAY: ['PG'],
  LINK_PAGO: ['LP', 'LK', 'TK'],
  LINK: ['LP', 'LK', 'TK'],
};

// Estatus de integrador elegibles en Cotizaciones / Proyectos Directos.
export const SELECTABLE_INTEGRATOR_STATUSES = ['Certificado', 'En proceso'];
export const isSelectableIntegrator = (i) => SELECTABLE_INTEGRATOR_STATUSES.includes(i?.integrator_status);

// ¿Todos los registros de ese nombre están "En proceso"? (para etiqueta visible)
export const isInProcessName = (rows, name) => {
  const recs = (rows || []).filter((r) => r.name === name);
  return recs.length > 0 && recs.every((r) => r.integrator_status === 'En proceso');
};

// Tipos de proyecto "pasarela" que muestran distintivo visual [PG]/[LP]/[TK].
const BADGE_PROJECT_TYPES = new Set(['GATEWAY', 'LINK_PAGO', 'LINK']);

export const allowedIntegrationTypes = (quoteType) =>
  PROJECT_TYPE_INTEGRATION[_norm(quoteType)] || null;

// Predicado (integration_type) => boolean según el Tipo de Proyecto.
// Tipo desconocido / no seleccionado → no filtra (devuelve true).
export const integratorTypeMatch = (quoteType) => {
  const allowed = allowedIntegrationTypes(quoteType);
  if (!allowed) return () => true;
  const set = new Set(allowed);
  return (t) => set.has(_norm(t));
};

// Compat: alias histórico usado en los formularios de cotización/proyecto.
export const integratorModalityMatch = integratorTypeMatch;

// ¿El tipo de proyecto debe mostrar el distintivo de tipo de integración?
export const shouldShowIntegrationBadge = (quoteType) =>
  BADGE_PROJECT_TYPES.has(_norm(quoteType));

// Devuelve los integration_type distintos asociados a un nombre de integrador
// dentro de una lista ya filtrada (para armar el sufijo/badge visible).
export const integrationTypesForName = (rows, name) =>
  Array.from(new Set((rows || [])
    .filter((r) => r.name === name)
    .map((r) => _norm(r.integration_type))
    .filter(Boolean)));

// Sufijo visible p.ej. "[PG]" o "[LP] [TK]" a partir de una lista de tipos.
export const formatIntegrationBadge = (types) =>
  (types || []).filter(Boolean).map((t) => `[${_norm(t)}]`).join(' ');
