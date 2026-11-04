# Iter356: retest de correcciones Edición Maestra (multistore sin rifs, certificadas bloqueadas, ruido de bitácora, catálogo de bancos).
# Cada proyecto tocado se respalda completo y se restaura exactamente con replace_one al final.
import os
import re
import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
MS = 'prj_4903ac85c83d'
MR = 'prj_9b08ebe9a4ef'
mdb = MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]


@pytest.fixture(scope='module', autouse=True)
def backup_restore():
    docs = {pid: mdb.projects.find_one({'project_id': pid}) for pid in (MS, MR)}
    yield
    for pid, d in docs.items():
        mdb.projects.replace_one({'_id': d['_id']}, d)


@pytest.fixture(scope='module')
def originals():
    return {pid: mdb.projects.find_one({'project_id': pid}) for pid in (MS, MR)}


@pytest.fixture(scope='module')
def s():
    sess = requests.Session()
    r = sess.post(f"{BASE_URL}/api/auth/login", json={"email": "rgonzalez@megasoft.com.ve", "password": "Mega2026*"})
    if r.status_code != 200:
        pytest.skip(f"login failed {r.status_code}")
    tok = r.json().get('session_token') or r.json().get('token')
    sess.headers.update({"Authorization": f"Bearer {tok}"})
    return sess


def proj(pid):
    return mdb.projects.find_one({'project_id': pid}, {'_id': 0})


def restore(originals, pid):
    mdb.projects.replace_one({'project_id': pid}, originals[pid])


def branches_of(p, default_client=''):
    rif_client = {r['rif_id']: r.get('client_id') for r in p.get('rifs') or []}
    return [{
        'store_id': st['store_id'], 'name': st.get('name') or '',
        'client_id': rif_client.get(st.get('rif_id')) or default_client,
        'box_count': st.get('box_count') or 0,
        'medios': [{'bank_name': b, 'product_name': pr} for b, ps in (st.get('implementation_matrix') or {}).items() for pr in ps],
    } for st in p['stores']]


def ui_payload(p, branches, repl=None):
    """Replica el payload completo que envía MasterEditDialog sin cambios del usuario."""
    return {
        'project_number': p.get('project_number') or '', 'client_id': p.get('client_id') or None,
        'client_name': p.get('client_name') or '', 'client_rif': p.get('client_rif') or '',
        'client_sede': p.get('client_sede') or '', 'total_usd': p.get('total_usd'), 'total_bs': p.get('total_bs'),
        'integrator_id': p.get('integrator_id') or None, 'integrator_name': p.get('integrator_name') or '',
        'integrator_app_name': p.get('integrator_app_name') or '', 'pinpad_model': p.get('pinpad_model') or '',
        'server_name': p.get('server_name') or '', 'ticket_number': p.get('ticket_number') or '',
        'status': p.get('status') or 'Por asignar', 'quote_type': (p.get('quote_type') or 'VPOS').upper(),
        'sponsoring_bank_name': p.get('sponsoring_bank_name') or '', 'sponsoring_bank_id': p.get('sponsoring_bank_id') or '',
        'sponsoring_processor_name': p.get('sponsoring_processor_name') or None,
        'generador_user_id': p.get('created_by_user_id') or '__none__',
        'hardware': [{'hardware_id': h.get('hardware_id'), 'name': h.get('name'), 'type': h.get('type')} for h in p.get('hardware') or []],
        'branches': branches, 'medio_replacements': repl or [],
    }


def put(s, pid, body):
    return s.put(f"{BASE_URL}/api/projects/{pid}/master-override", json=body)


# --- FIX: multistore sin tocar RIF no crea rifs[] ---
class TestMultistoreNoRifs:
    def test_save_with_empty_client_no_rifs(self, s, originals):
        p = proj(MS)
        r = put(s, MS, ui_payload(p, branches_of(p)))
        assert r.status_code == 200, r.text
        after = proj(MS)
        assert 'rifs' not in after
        assert all(not st.get('rif_id') for st in after['stores'])
        restore(originals, MS)

    def test_save_with_own_client_no_rifs(self, s, originals):
        p = proj(MS)
        r = put(s, MS, ui_payload(p, branches_of(p, p['client_id'])))
        assert r.status_code == 200, r.text
        after = proj(MS)
        assert 'rifs' not in after
        assert all(not st.get('rif_id') for st in after['stores'])
        restore(originals, MS)


# --- Bitácora sin ruido ---
class TestAuditNoise:
    def _last_entry(self, pid):
        return proj(pid)['bitacora'][-1]

    def test_multistore_no_changes(self, s, originals):
        p = proj(MS)
        r = put(s, MS, ui_payload(p, branches_of(p)))
        assert r.status_code == 200
        e = self._last_entry(MS)
        print('MS changes:', e['changes'])
        labels = [c['label'] for c in e['changes']]
        assert 'Generador' not in labels
        assert 'Bancos/Productos' not in labels
        assert r.json()['changes_count'] == 0, e['text']
        restore(originals, MS)

    def test_multirif_no_changes(self, s, originals):
        p = proj(MR)
        r = put(s, MR, ui_payload(p, branches_of(p)))
        assert r.status_code == 200, r.text
        e = self._last_entry(MR)
        print('MR changes:', e['changes'])
        assert r.json()['changes_count'] == 0, e['text']
        restore(originals, MR)


# --- NUEVO: sucursal certificada bloqueada ---
class TestCertifiedLock:
    def test_change_boxes_certified_400(self, s, originals):
        p = proj(MR)
        b = branches_of(p)
        idx = next(i for i, x in enumerate(b) if x['name'] == 'Carbon')
        b[idx]['box_count'] = 5
        r = put(s, MR, ui_payload(p, b))
        assert r.status_code == 400
        assert 'está certificada' in r.json()['detail']
        assert proj(MR)['stores'] == originals[MR]['stores']

    def test_remove_medio_certified_400(self, s, originals):
        p = proj(MR)
        b = branches_of(p)
        b[0]['medios'] = []
        r = put(s, MR, ui_payload(p, b))
        assert r.status_code == 400
        assert 'está certificada' in r.json()['detail']

    def test_certified_rename_ok(self, s, originals):
        p = proj(MR)
        b = branches_of(p)
        b[0]['name'] = 'TEST_Renombrada'
        r = put(s, MR, ui_payload(p, b))
        assert r.status_code == 200, r.text
        assert proj(MR)['stores'][0]['name'] == 'TEST_Renombrada'
        restore(originals, MR)


# --- Catálogo de bancos: nombre normalizado para reemplazos ---
class TestBankCatalogMatch:
    @staticmethod
    def norm(n):
        return re.sub(r'\s*\([^)]*\)\s*$', '', n or '').strip().lower()

    @pytest.mark.parametrize('bank', ['Banco Nacional de Crédito (BNC)', 'Banco Fondo Común (BFC)'])
    def test_catalog_has_alternatives(self, s, bank):
        r = s.get(f"{BASE_URL}/api/banks")
        assert r.status_code == 200
        data = r.json()
        banks = data if isinstance(data, list) else data.get('banks', [])
        match = [b for b in banks if b.get('name') == bank] or [b for b in banks if self.norm(b.get('name')) == self.norm(bank)]
        assert match, f"no se encontró {bank} en el catálogo"
        prods = [p['product_name'] for p in match[0].get('products') or [] if p.get('vpos_available')]
        print(bank, '->', prods)
        assert len(prods) >= 2
