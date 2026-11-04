# Iter357: Comercio/RIF de sucursal libre (cualquier cliente de la BD) + validación client_id inexistente.
# Respalda y restaura exactamente con replace_one los proyectos tocados.
import pytest
from test_master_branches_iter356 import (BASE_URL, MS, MR, mdb, proj, branches_of, ui_payload, put)  # noqa
import requests

EXT = 'cli_000ab967b9fc'
EXT_RIF = 'J506385619'


@pytest.fixture(scope='module', autouse=True)
def backup_restore():
    docs = {pid: mdb.projects.find_one({'project_id': pid}) for pid in (MS, MR)}
    yield
    for pid, d in docs.items():
        mdb.projects.replace_one({'_id': d['_id']}, d)
    for pid, d in docs.items():
        assert mdb.projects.find_one({'_id': d['_id']}) == d


@pytest.fixture(scope='module')
def s():
    sess = requests.Session()
    r = sess.post(f"{BASE_URL}/api/auth/login", json={"email": "rgonzalez@megasoft.com.ve", "password": "Mega2026*"})
    if r.status_code != 200:
        pytest.skip("login failed")
    sess.headers.update({"Authorization": f"Bearer {r.json().get('session_token') or r.json().get('token')}"})
    return sess


@pytest.mark.parametrize('pid', [MR, MS])
def test_add_external_client_branch(s, pid):
    orig = mdb.projects.find_one({'project_id': pid})
    p = proj(pid)
    br = branches_of(p, '' if p.get('rifs') else (p.get('client_id') or ''))
    br.append({'store_id': None, 'name': 'TEST_Externa', 'client_id': EXT, 'box_count': 0, 'medios': []})
    r = put(s, pid, ui_payload(p, br, p.get('medio_replacements') or []))
    assert r.status_code == 200, r.text
    after = proj(pid)
    rif = next((x for x in after.get('rifs') or [] if x.get('client_id') == EXT), None)
    assert rif and rif['rif'] == EXT_RIF
    st = next(x for x in after['stores'] if x['name'] == 'TEST_Externa')
    assert st['rif_id'] == rif['rif_id']
    mdb.projects.replace_one({'_id': orig['_id']}, orig)


@pytest.mark.parametrize('pid', [MR, MS])
def test_nonexistent_client_400(s, pid):
    p = proj(pid)
    br = branches_of(p, '' if p.get('rifs') else (p.get('client_id') or ''))
    br.append({'store_id': None, 'name': 'TEST_Bad', 'client_id': 'cli_TEST_noexiste', 'box_count': 0, 'medios': []})
    r = put(s, pid, ui_payload(p, br, p.get('medio_replacements') or []))
    assert r.status_code == 400
    assert 'no existe en Clientes' in r.text
    assert proj(pid)['stores'] == p['stores']
