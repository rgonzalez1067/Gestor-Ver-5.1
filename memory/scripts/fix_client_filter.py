p = '/app/frontend/src/components/quotes/QuoteFilters.jsx'
s = open(p).read()
def rep(old, new):
    global s
    assert s.count(old) == 1, old[:70]
    s = s.replace(old, new)

rep("""const SearchableSelect = ({ items, value, onChange, allLabel, placeholder, testid }) => {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
""", """const SearchableSelect = ({ items, value, onChange, allLabel, placeholder, testid, allowQueryMatch = false }) => {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [queryLabel, setQueryLabel] = useState('');
""")
rep("""    const found = items.find((g) => g.value === value);
    return found ? found.label : 'Filtrado';
  }, [value, items, allLabel]);
""", """    const found = items.find((g) => g.value === value);
    return found ? found.label : (queryLabel || 'Filtrado');
  }, [value, items, allLabel, queryLabel]);

  // Aplica a la grilla todas las coincidencias del texto escrito (razón social o fantasía).
  const applyQueryMatch = () => {
    const q = query.trim();
    if (!allowQueryMatch || !q || filtered.length === 0) return;
    if (filtered.length === 1) {
      onChange(filtered[0].value);
    } else {
      const ids = Array.from(new Set(filtered.flatMap((g) => g.value.split(','))));
      onChange(ids.join(','));
      setQueryLabel(`Coincidencias: "${q}" (${filtered.length})`);
    }
    setOpen(false);
    setQuery('');
  };
""")
rep("""              onChange={(e) => setQuery(e.target.value)}
              placeholder={placeholder}""", """              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); applyQueryMatch(); } }}
              placeholder={placeholder}""")
rep("""          {filtered.length === 0 && (
            <p className="px-3 py-3 text-xs text-slate-400 text-center">Sin coincidencias</p>
          )}""", """          {allowQueryMatch && query.trim() && filtered.length > 1 && (
            <button
              type="button"
              className="w-full text-left px-3 py-1.5 text-sm bg-blue-50/60 hover:bg-blue-100 text-blue-700 font-medium border-b"
              onClick={applyQueryMatch}
              data-testid={`${testid}-option-query-match`}>
              Ver todas las coincidencias de "{query.trim()}" ({filtered.length})
            </button>
          )}
          {filtered.length === 0 && (
            <p className="px-3 py-3 text-xs text-slate-400 text-center">Sin coincidencias</p>
          )}""")
rep("""    allLabel="Todos los clientes" placeholder="Buscar razón social o fantasía..." testid="filter-client" />;""",
    """    allLabel="Todos los clientes" placeholder="Buscar razón social o fantasía (Enter aplica)" testid="filter-client" allowQueryMatch />;""")
open(p, 'w').write(s)
print('ok')
