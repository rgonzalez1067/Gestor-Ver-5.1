"""Detecta integradores duplicados (mismo integrador, aplicativo parecido y mismo tipo) y exporta a Excel."""
import asyncio
import json
import os
import re
import sys
import unicodedata
from datetime import datetime
from difflib import SequenceMatcher

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

load_dotenv('/app/backend/.env')
OUT = sys.argv[1] if len(sys.argv) > 1 else '/app/frontend/public/exports/integradores_duplicados.xlsx'
LEGAL = r'\b(c ?a|s ?a|s ?r ?l|s ?a ?s|inc|llc|corp|ltd|cia|compania|grupo)\b'
APP_NOISE = r'\b(version|ver|v|release|rel|edicion|ed)\b'
SIM = 0.85


def _base(s):
    s = unicodedata.normalize('NFKD', str(s or '')).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', ' ', s)


def norm_name(s):
    return re.sub(r'\s+', ' ', re.sub(LEGAL, ' ', _base(s))).strip()


def norm_app(s):
    return re.sub(r'\s+', ' ', re.sub(APP_NOISE, ' ', _base(s))).strip()


def similar(a, b):
    if a == b:
        return True
    if not a or not b:
        return False
    return SequenceMatcher(None, a.replace(' ', ''), b.replace(' ', '')).ratio() >= SIM


def flat(v):
    if v is None:
        return ''
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False, default=str)
    return v if isinstance(v, (int, float, bool)) else str(v)


async def main():
    db = AsyncIOMotorClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
    recs = await db.integrators.find({}, {'_id': 0}).to_list(None)
    buckets = {}
    for r in recs:
        key = (norm_name(r.get('name')), _base(r.get('integration_type')).strip())
        if key[0]:
            buckets.setdefault(key, []).append(r)

    groups = []
    for _, items in buckets.items():
        if len(items) < 2:
            continue
        clusters = []
        for r in items:
            a = norm_app(r.get('app_name'))
            for c in clusters:
                if any(similar(a, norm_app(x.get('app_name'))) for x in c):
                    c.append(r)
                    break
            else:
                clusters.append([r])
        groups += [c for c in clusters if len(c) > 1]
    groups.sort(key=lambda g: (norm_name(g[0].get('name')), -len(g)))

    cert_keys = sorted({k for r in recs for k in (r.get('certifications') or {})})
    base_keys = []
    for r in recs:
        for k in r:
            if k not in base_keys and k != 'certifications':
                base_keys.append(k)

    wb = Workbook()
    hdr_font, hdr_fill = Font(bold=True, color='FFFFFF'), PatternFill('solid', fgColor='1E3A5F')
    fills = [PatternFill('solid', fgColor='FFF7E0'), PatternFill('solid', fgColor='E8F1FB')]

    ws = wb.active
    ws.title = 'Resumen'
    ws.append([f'Integradores duplicados — generado {datetime.now().strftime("%d/%m/%Y %H:%M")}'])
    ws['A1'].font = Font(bold=True, size=13)
    ws.append([f'Registros analizados: {len(recs)} · Grupos duplicados: {len(groups)} · Registros involucrados: {sum(len(g) for g in groups)}'])
    ws.append([])
    head = ['Grupo', 'Integrador', 'Tipo de Integración', 'Aplicativos registrados', 'Cantidad', 'IDs', 'Estatus', 'Implementadores']
    ws.append(head)
    for c in range(1, len(head) + 1):
        ws.cell(row=4, column=c).font, ws.cell(row=4, column=c).fill = hdr_font, hdr_fill
    for i, g in enumerate(groups, 1):
        ws.append([f'G{i:03d}', g[0].get('name'), g[0].get('integration_type'),
                   ' | '.join(sorted({str(x.get('app_name') or '') for x in g})), len(g),
                   ', '.join(x.get('integrator_id', '') for x in g),
                   ' | '.join(str(x.get('integrator_status') or '') for x in g),
                   ' | '.join(sorted({str(x.get('implementador') or '') for x in g}))])
        for c in range(1, len(head) + 1):
            ws.cell(row=ws.max_row, column=c).fill = fills[i % 2]
    for col, w in zip('ABCDEFGH', (8, 38, 16, 50, 10, 40, 30, 30)):
        ws.column_dimensions[col].width = w

    wd = wb.create_sheet('Detalle Registros')
    cols = ['Grupo'] + base_keys + [f'cert:{k}' for k in cert_keys]
    wd.append(cols)
    for c in range(1, len(cols) + 1):
        cell = wd.cell(row=1, column=c)
        cell.font, cell.fill, cell.alignment = hdr_font, hdr_fill, Alignment(wrap_text=True, vertical='center')
    for i, g in enumerate(groups, 1):
        for r in sorted(g, key=lambda x: str(x.get('created_at') or '')):
            certs = r.get('certifications') or {}
            wd.append([f'G{i:03d}'] + [flat(r.get(k)) for k in base_keys] + [flat(certs.get(k)) for k in cert_keys])
            for c in range(1, len(cols) + 1):
                wd.cell(row=wd.max_row, column=c).fill = fills[i % 2]
    for c in range(1, len(cols) + 1):
        wd.column_dimensions[get_column_letter(c)].width = 22
    wd.freeze_panes = 'C2'
    wd.auto_filter.ref = wd.dimensions

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    wb.save(OUT)
    print(f'{len(recs)} registros · {len(groups)} grupos · {sum(len(g) for g in groups)} involucrados → {OUT}')
    for i, g in enumerate(groups[:15], 1):
        print(f'G{i:03d}', g[0].get('name'), '|', g[0].get('integration_type'), '|', [x.get('app_name') for x in g])


asyncio.run(main())
