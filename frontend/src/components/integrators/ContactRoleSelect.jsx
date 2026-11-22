export const CONTACT_ROLES = ['Contacto Principal', 'Responsable Técnico', 'Contacto Administrativo', 'Comercial'];

// Rol fijo; si el contacto trae un rol anterior fuera de la lista se conserva como opción.
export const ContactRoleSelect = ({ value, onChange, className = '', testId }) => (
  <select value={value || ''} onChange={(e) => onChange(e.target.value)} data-testid={testId}
    className={`rounded-md border border-input bg-white px-2 text-xs ${className}`}>
    <option value="">Rol...</option>
    {value && !CONTACT_ROLES.includes(value) && <option value={value}>{value}</option>}
    {CONTACT_ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
  </select>
);
