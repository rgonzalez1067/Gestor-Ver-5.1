# Edición Maestra: sucursales / RIFs / topes de cajas y medios (multistore, multirif) + regresión single.
# Cada proyecto tocado se respalda completo y se restaura exactamente con replace_one al final.
import os
import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
MS = 'prj_4903ac85c83d'
MR = 'prj_9b08ebe9a4ef'
SINGLE = 'prj_25f4b646cd7c'
GROUP_CLIENT = 'cli_2657337835da'

mdb = MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]


@pytest.fixture(scope='module', autouse=True)
def backup_restore():
    docs = {pid: mdb.projects.find_one({'project_id': pid}) for pid in (MS, MR, SINGLE)}
    yield
    for pid, d in docs.items():
        mdb.projects.replace_one({'_id': d['_id']}, d)


@pytest.fixture(scope='module')
def s():
    sess = requests.Session()
    r = sess.post(f"{BASE_URL}/api/auth/login", json={"email": "rgonzalez@megasoft.com.ve", "password": "Mega2026*"})
    if r.status_code != 200:
        pytest.skip(f"login failed {r.status_code}")
    tok = r.json().get('session_token') or r.json().get('token')
    sess.headers.update({"Authorization": f"Bearer {tok}"})
    return sess


def restore(pid, doc):
    mdb.projects.replace_one({'project_id': pid}, doc)


def proj(pid):
    return mdb.projects.find_one({'project_id': pid}, {'_id': 0})


def branches_of(p):
    rif_client = {r['rif_id']: r.get('client_id') for r in p.get('rifs') or []}
    out = []
    for st in p['stores']:
        out.append({
            'store_id': st['store_id'], 'name': st.get('name') or '',
            'client_id': rif_client.get(st.get('rif_id')),
            'box_count': st.get('box_count') or 0,
            'medios': [{'bank_name': b, 'product_name': pr} for b, ps in (st.get('implementation_matrix') or {}).items() for pr in ps],
        })
    return out


def put(s, pid, branches, repl=None, **extra):
    body = {'branches': branches, 'medio_replacements': repl or [], **extra}
    return s.put(f"{BASE_URL}/api/projects/{pid}/master-override", json=body)


# --- Context endpoint ---
class TestContext:
    def test_multistore_context(self, s):
        r = s.get(f"{BASE_URL}/api/projects/{MS}/master-branches-context")
        assert r.status_code == 200, r.text
        d = r.json()
        assert d['baseline']['total_boxes'] == 2
        assert len(d['baseline']['medios']) == 4
        assert all(v == 2 for v in d['baseline']['medios'].values())
        assert d['certified_store_ids'] == []
        assert isinstance(d['eligible_clients'], list) and d['medio_replacements'] == []

    def test_multirif_context(self, s):
        d = s.get(f"{BASE_URL}/api/projects/{MR}/master-branches-context").json()
        assert d['baseline']['total_boxes'] == 28
        assert d['baseline']['medios'] == {'Banco Fondo Común (BFC)|Verificación Pago Movil': 28}
        assert set(d['certified_store_ids']) == {'st_ea2196b8', 'st_4183e280', 'st_7118a405'}
        ids = {c['client_id'] for c in d['eligible_clients']}
        assert GROUP_CLIENT in ids and len(ids) >= 4
        assert all('_id' not in c for c in d['eligible_clients'])

    def test_context_404(self, s):
        assert s.get(f"{BASE_URL}/api/projects/prj_nope/master-branches-context").status_code == 404

    def test_context_requires_auth(self):
        assert requests.get(f"{BASE_URL}/api/projects/{MS}/master-branches-context").status_code in (401, 403)


# --- Validaciones multistore ---
class TestMultistoreValidation:
    def test_box_excess(self, s):
        b = branches_of(proj(MS)); b[0]['box_count'] = 2
        r = put(s, MS, b)
        assert r.status_code == 400
        assert r.json()['detail'] == 'Límite Excedido: La sumatoria de cajas asignadas (3) supera el tope máximo de cajas contratadas en el proyecto (2).'

    def test_uncontracted_medio(self, s):
        b = branches_of(proj(MS)); b[0]['medios'].append({'bank_name': 'Banco Mercantil', 'product_name': 'TEST_Botón'})
        r = put(s, MS, b)
        assert r.status_code == 400 and r.json()['detail'].startswith('Producto no contratado')

    def test_medio_over_cap_via_replacement_share(self, s):
        # 'Cambio Pago Movil' (BNC) cap 2; reemplazo TEST_P2P comparte tope; both stores with 1 box using old + a third... total cap=2 so use medio sharing
        b = branches_of(proj(MS))
        repl = [{'bank_name': 'Banco Nacional de Crédito (BNC)', 'from_product': 'Cambio Pago Movil', 'to_product': 'TEST_P2P'}]
        # store0 uses Cambio (1) + TEST_P2P (1) => group usage 2 + store1 Cambio (1) => 3 > 2
        b[0]['medios'].append({'bank_name': 'Banco Nacional de Crédito (BNC)', 'product_name': 'TEST_P2P'})
        r = put(s, MS, b, repl)
        assert r.status_code == 400, r.text
        assert 'tope contratado es 2' in r.json()['detail']

    def test_invalid_replacement(self, s):
        repl = [{'bank_name': 'Banco Mercantil', 'from_product': 'NoExiste', 'to_product': 'TEST_X'}]
        r = put(s, MS, branches_of(proj(MS)), repl)
        assert r.status_code == 400 and r.json()['detail'].startswith('Reemplazo inválido')

    def test_empty_name(self, s):
        b = branches_of(proj(MS)); b[0]['name'] = '  '
        assert put(s, MS, b).status_code == 400

    def test_negative_boxes(self, s):
        b = branches_of(proj(MS)); b[0]['box_count'] = -1
        r = put(s, MS, b)
        assert r.status_code == 400, r.text

    def test_ineligible_rif(self, s):
        b = branches_of(proj(MS)); b[0]['client_id'] = 'cli_inexistente_xyz'  # cualquier comercio vale, pero debe existir
        r = put(s, MS, b)
        assert r.status_code == 400 and 'no existe en Clientes' in r.json()['detail']


# --- Flujos exitosos multistore ---
class TestMultistoreSave:
    def test_replacement_accepted_and_phase_preserved(self, s):
        orig = proj(MS)
        b = branches_of(orig)
        # store1: quitar 'Cambio Pago Movil ' de BNC y usar el reemplazo TEST_P2P
        b[1]['medios'] = [m for m in b[1]['medios'] if not (m['bank_name'].startswith('Banco Nacional') and m['product_name'].strip() == 'Cambio Pago Movil')]
        b[1]['medios'].append({'bank_name': 'Banco Nacional de Crédito (BNC)', 'product_name': 'TEST_P2P'})
        repl = [{'bank_name': 'Banco Nacional de Crédito (BNC)', 'from_product': 'Cambio Pago Movil', 'to_product': 'TEST_P2P'}]
        r = put(s, MS, b, repl)
        assert r.status_code == 200, r.text
        p = proj(MS)
        st0 = p['stores'][0]
        o0 = orig['stores'][0]
        # fase preservada (producto con espacio final)
        for bn, ps in o0['implementation_matrix'].items():
            for pr, data in ps.items():
                assert st0['implementation_matrix'][bn][pr.strip()] == data
        assert 'TEST_P2P' in p['stores'][1]['implementation_matrix']['Banco Nacional de Crédito (BNC)']
        assert p['medio_replacements'] == repl
        assert p['contract_baseline']['total_boxes'] == 2
        assert 'TEST_P2P' in p['implementation_matrix']['Banco Nacional de Crédito (BNC)']
        ctx = s.get(f"{BASE_URL}/api/projects/{MS}/master-branches-context").json()
        assert ctx['medio_replacements'] == repl
        restore(MS, orig)

    def test_add_and_remove_branch(self, s):
        orig = proj(MS)
        b = branches_of(orig)
        removed = b.pop(1)
        b.append({'store_id': None, 'name': 'TEST_Nueva', 'client_id': None, 'box_count': 1,
                  'medios': [{'bank_name': 'Banco Mercantil', 'product_name': 'Verificación Pago Movil'}]})
        r = put(s, MS, b)
        assert r.status_code == 200, r.text
        p = proj(MS)
        ids = [x['store_id'] for x in p['stores']]
        assert removed['store_id'] not in ids and len(ids) == 2
        new = p['stores'][1]
        assert new['store_id'].startswith('st_') and new['name'] == 'TEST_Nueva' and new['box_count'] == 1
        assert new['implementation_matrix'] == {'Banco Mercantil': {'Verificación Pago Movil': {}}}
        restore(MS, orig)

    def test_multistore_no_rifs_side_effect_with_project_client(self, s):
        """UI envía client_id = p.client_id por defecto en multistore: verificar si crea rifs[]."""
        orig = proj(MS)
        b = branches_of(orig)
        for x in b:
            x['client_id'] = orig['client_id']
        r = put(s, MS, b)
        assert r.status_code == 200, r.text
        p = proj(MS)
        print('RIFS AFTER multistore save:', p.get('rifs'))
        restore(MS, orig)


# --- Multirif ---
class TestMultirif:
    def test_delete_certified_blocked(self, s):
        b = branches_of(proj(MR)); b.pop(2)
        r = put(s, MR, b)
        assert r.status_code == 400 and 'certificada' in r.json()['detail']

    def test_group_client_added_to_rifs(self, s):
        orig = proj(MR)
        b = branches_of(orig)
        b[2]['box_count'] = 5
        r = put(s, MR, b)
        assert r.status_code == 400 and 'certificada' in r.json()['detail']
        b[2]['box_count'] = 10
        # Para tener margen, se libera capacidad solo si el baseline lo permite: 28 contratadas = 28 asignadas
        b.append({'store_id': None, 'name': 'TEST_GrupoSuc', 'client_id': GROUP_CLIENT, 'box_count': 0,
                  'medios': [{'bank_name': 'Banco Fondo Común (BFC)', 'product_name': 'Verificación Pago Movil'}]})
        r = put(s, MR, b)
        assert r.status_code == 200, r.text
        p = proj(MR)
        rifs = {r_['client_id']: r_ for r_ in p['rifs']}
        assert GROUP_CLIENT in rifs and rifs[GROUP_CLIENT]['box_count'] == 0
        assert rifs['cli_bd12925ab654']['box_count'] == 10
        assert rifs['cli_874a6ea688e9']['box_count'] == 8
        new = p['stores'][3]
        assert new['rif_id'] == rifs[GROUP_CLIENT]['rif_id']
        # fases certificadas preservadas
        for i in range(3):
            assert p['stores'][i]['implementation_matrix'] == orig['stores'][i]['implementation_matrix']
        restore(MR, orig)

    def test_multirif_excess(self, s):
        b = branches_of(proj(MR)); b[0]['box_count'] = 9
        r = put(s, MR, b)
        assert r.status_code == 400 and '(29)' in r.json()['detail'] and '(28)' in r.json()['detail']


# --- Regresión single + servidor ---
class TestSingle:
    def test_single_banks_products_and_server(self, s):
        orig = proj(SINGLE)
        bps = [{'bank_name': bn, 'products': list(ps.keys())} for bn, ps in orig['implementation_matrix'].items()]
        r = s.put(f"{BASE_URL}/api/projects/{SINGLE}/master-override", json={'banks_products': bps, 'server_name': 'Forum'})
        assert r.status_code == 200, r.text
        p = proj(SINGLE)
        assert p['server_name'] == 'Forum'
        assert p['implementation_matrix'] == {bn: {k.strip(): v for k, v in ps.items()} for bn, ps in orig['implementation_matrix'].items()}
        restore(SINGLE, orig)

    def test_single_ignores_branches(self, s):
        orig = proj(SINGLE)
        r = s.put(f"{BASE_URL}/api/projects/{SINGLE}/master-override", json={'branches': []})
        assert r.status_code == 200
        assert proj(SINGLE).get('stores') == orig.get('stores')
        restore(SINGLE, orig)
