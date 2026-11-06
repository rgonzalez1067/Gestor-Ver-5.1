import sys
sys.path.insert(0, '/app/backend')
import fitz
from services.hoja_ruta_pdf import generate_nota_entrega_pdf
from services.transfer_note_pdf import generate_transfer_note_pdf
from services.temporary_assignment_pdf import generate_temporary_assignment_pdf

items = [{'name': f'POS Modelo {i}', 'type': 'POS', 'quantity': 30, 'serials': [f'SN{i}{j:04d}' for j in range(30)]} for i in range(6)]
LOGO = '/app/backend/uploads/logo.png'

def dump(name, data):
    b = data if isinstance(data, bytes) else data.getvalue()
    open(f'/tmp/{name}.pdf', 'wb').write(b)
    d = fitz.open(f'/tmp/{name}.pdf')
    print(name, 'pages', len(d))
    for i in range(min(2, len(d))):
        d[i].get_pixmap(dpi=45, clip=fitz.Rect(0, 0, 612, 300)).save(f'/app/memory/{name}_{i}.png')

dump('ne', generate_nota_entrega_pdf('NE-2026-0001', 'COT-1', 'PRJ-1', 'Cliente', 'J1', 'Dir', 'Ana', '0414', 'Principal', items, 'Admin', logo_path=LOGO))
dump('trf', generate_transfer_note_pdf('TRF-2026-0001', 'A', 'Juan', 'V1', 'B', 'Pedro', items, 'Admin', logo_path=LOGO))
dump('tmp', generate_temporary_assignment_pdf({'assignment_number': 'AT-1', 'items': items}, items))
