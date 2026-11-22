export const PAYLOAD_KEYS = ['name', 'integrator_type', 'integration_type', 'app_name', 'integration_modality', 'integrator_status', 'gestor',
  'categoria', 'ticket_number', 'certifications', 'last_contact_date', 'contacts', 'integration_phase', 'coordinador', 'coordinador_user_id',
  'implementador', 'implementador_user_id', 'project_start_date', 'project_name', 'observations', 'comercios_relacionados',
  'componente_version', 'productos_certificar', 'correo_eventual', 'project_scope', 'principal_contact_name', 'principal_contact_phone',
  'principal_contact_email', 'interface_negotiation', 'test_env_start_date', 'test_env_end_date', 'empresa_integradora_id'];

export const INTEGRATION_TYPES = ['CR', 'LP', 'PG', 'MP', 'TK'];
export const INTEGRATION_MODALITIES = ['Bridge PG', 'MPOS', 'PG Modalidad Universal', 'PG Modalidad No Universal', 'Rest', 'Stand Alone', 'Web Link de Pago Modalidad No Universal', 'Web Link de Pago Modalidad Universal', 'Wrapper', 'Web Tokenizador Modalidad No Universal con Verificación de Micro', 'Web Tokenizador Modalidad No Universal sin Verificación de Micro', 'Web Tokenizador Modalidad Universal con Verificación de Micro', 'Web Tokenizador Modalidad Universal Sin Verificación de Micro', 'Linux'];
export const PHASES = ['Negociación', 'Desarrollo', 'QA', 'SQA', 'Producción'];
export const CERT_STATES = {
  C: { label: 'C', text: 'Certificado', color: 'bg-emerald-100 text-emerald-700 border-emerald-300' },
  P: { label: 'P', text: 'Pendiente', color: 'bg-amber-100 text-amber-700 border-amber-300' },
  'N/A': { label: 'N/A', text: 'No Aplica', color: 'bg-[#E3F2FD] text-[#0D47A1] border-[#90CAF9]' },
};
export const CERT_CYCLE = ['P', 'C', 'N/A'];

const ACTIVE_SCOPES = ['new', 'component', 'expansion', 'test_environment'];
export const isActiveApp = (i) => !!i && ACTIVE_SCOPES.includes(i.project_scope) && i.integrator_status !== 'Cerrado';
export const isLockedApp = (i) => !!i && ['Certificado', 'Cerrado'].includes(i.integrator_status) && !isActiveApp(i);

// PUT /integrators/{id} reemplaza la ficha completa: se reenvía todo el registro + el parche.
export const buildPayload = (intg, patch = {}) => {
  const out = {};
  PAYLOAD_KEYS.forEach((k) => { if (intg[k] !== undefined && intg[k] !== null) out[k] = intg[k]; });
  Object.assign(out, patch);
  if (out.integrator_status === 'Cerrado') delete out.integrator_status;
  out.contacts = (out.contacts || []).filter((c) => (c.name || '').trim());
  return out;
};
