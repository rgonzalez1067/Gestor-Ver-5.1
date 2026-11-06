import re, glob
files = [f for f in glob.glob('/app/backend/**/*.py', recursive=True) if '/tests/' not in f and 'rebrand' not in f] + \
        glob.glob('/app/frontend/src/**/*.jsx', recursive=True) + glob.glob('/app/frontend/src/**/*.js', recursive=True)
changed = []
for f in files:
    s = open(f, encoding='utf-8').read()
    if 'MegaNexus' not in s:
        continue
    n = s
    for a, b in [('MegaNexus ("Gestor")', 'Gestor - CRM'), ('MegaNexus (Gestor)', 'Gestor - CRM'),
                 ('Gestor MegaNexus', 'Gestor - CRM'), ('MegaNexus Gestor', 'Gestor - CRM'),
                 ('Gestor | MegaNexus', 'Gestor - CRM')]:
        n = n.replace(a, b)
    # Conserva nombres de archivo existentes (Manual_Usuario_MegaNexus.docx)
    n = re.sub(r'(?<!_)MegaNexus(?!\.docx)', 'Gestor - CRM', n)
    if n != s:
        open(f, 'w', encoding='utf-8').write(n)
        changed.append(f)
print('\n'.join(changed))
