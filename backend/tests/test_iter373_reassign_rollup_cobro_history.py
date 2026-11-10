# Iter373: (A) reassign keeps status, (B) master-override rollup weighted by boxes,
# (D) cobro recurrente on direct projects, (F) quote-history segmentation by department.
import os, uuid, asyncio
import pytest, requests
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
load_dotenv('/app/frontend/.env')
BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
ADMIN = ("rgonzalez@megasoft.com.ve", "MegaSoft2026*")
PYME = ("jdolande@megasoft.com.ve", "QaMegaSoft2026*x")
CORP = ("mmartin@megasoft.com.ve", "QaMegaSoft2026*x")
IMPL_A = "user_3cc63615f2c0"  # Omar Jiménez (Implementador)
IMPL_B = "user_4f7c4697b820"  # Jhondder Oliveros (Implementador)
PH = ["Recibido", "Configurado", "Testeado", "En Producción"]


def _db_run(coro_fn):
    async def w():
        db = AsyncIOMotorClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
        return await coro_fn(db)
    return asyncio.new_event_loop().run_until_complete(w())


def _login(email, pwd):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": pwd})
    if r.status_code != 200 or not r.json().get("session_token"):
        pytest.skip(f"login failed {email}: {r.status_code} {r.text[:200]}")
    s = requests.Session()
    s.headers["Authorization"] = f"Bearer {r.json()['session_token']}"
    return s


@pytest.fixture(scope="module")
def admin():
    return _login(*ADMIN)


created = []


@pytest.fixture(scope="module", autouse=True)
def cleanup():
    yield
    async def d(db):
        await db.projects.delete_many({"project_id": {"$in": created}})
    if created:
        _db_run(d)


def _mk(status, assigned=True, ticket="T-373", extra=None):
    pid = f"prj_t373_{uuid.uuid4().hex[:8]}"
    doc = {"project_id": pid, "project_number": f"TEST_373_{pid[-4:]}", "client_name": "TEST_373 Cliente",
           "status": status, "ticket_number": ticket, "notes": [], "bitacora": [], "client_segment": "PYME",
           "implementation_matrix": {}, "project_type": "single", "created_at": "2026-01-01T00:00:00+00:00"}
    if assigned:
        doc.update({"assigned_to_user_id": IMPL_A, "assigned_to_name": "Omar Jiménez"})
    doc.update(extra or {})
    _db_run(lambda db: db.projects.insert_one(dict(doc)))
    created.append(pid)
    return pid


def _get(pid):
    return _db_run(lambda db: db.projects.find_one({"project_id": pid}, {"_id": 0}))


# ---- (A) Individual reassign keeps status ----
class TestAssign:
    @pytest.mark.parametrize("status", ["En Gestión", "Implementado parcial", "Suspendido", "Asignado"])
    def test_reassign_keeps_status(self, admin, status):
        pid = _mk(status)
        r = admin.put(f"{BASE_URL}/api/projects/{pid}/assign", json={"assigned_to_user_id": IMPL_B, "reassignment_comment": "TEST_373"})
        assert r.status_code == 200, r.text
        p = _get(pid)
        assert p["status"] == status
        assert p["assigned_to_user_id"] == IMPL_B
        assert any("reasignado" in (n.get("text") or "").lower() and "Omar" in n.get("text", "") for n in p["notes"])

    def test_por_asignar_goes_asignado(self, admin):
        pid = _mk("Por asignar", assigned=False, ticket="")
        r = admin.put(f"{BASE_URL}/api/projects/{pid}/assign", json={"assigned_to_user_id": IMPL_B})
        assert r.status_code == 200, r.text
        assert _get(pid)["status"] == "Asignado"

    def test_por_asignar_with_ticket_goes_en_gestion(self, admin):
        pid = _mk("Por asignar", assigned=False, ticket="99999")
        r = admin.put(f"{BASE_URL}/api/projects/{pid}/assign", json={"assigned_to_user_id": IMPL_B})
        assert r.status_code == 200
        assert _get(pid)["status"] == "En Gestión"

    def test_bulk_reassign_keeps_status(self, admin):
        p1, p2 = _mk("Suspendido"), _mk("Implementado parcial")
        r = admin.post(f"{BASE_URL}/api/projects/bulk-reassign", json={"to_user_id": IMPL_B, "project_ids": [p1, p2]})
        assert r.status_code == 200, r.text
        assert r.json()["reassigned"] == 2
        for pid, st in ((p1, "Suspendido"), (p2, "Implementado parcial")):
            p = _get(pid)
            assert p["status"] == st and p["assigned_to_user_id"] == IMPL_B
            assert any("Estatus conservado: " + st in n.get("text", "") for n in p["notes"])


# ---- (B) Master override rollup weighted by boxes ----
def _phases(done):
    return {ph: {"completed": done} for ph in PH}


class TestMasterRollup:
    def test_add_branch_recalculates_weighted(self, admin):
        stores = [
            {"store_id": "st_a373", "name": "A", "box_count": 3, "status": "Pendiente",
             "implementation_matrix": {"BANCO X": {"VPOS": _phases(True)}}},
            {"store_id": "st_b373", "name": "B", "box_count": 1, "status": "Pendiente",
             "implementation_matrix": {"BANCO X": {"VPOS": _phases(False)}}},
        ]
        pid = _mk("En Gestión", extra={"project_type": "multistore", "stores": stores, "box_count": 10,
                                       "implementation_matrix": {"BANCO X": {"VPOS": {}}},
                                       "contract_baseline": {"total_boxes": 10, "medios": {"BANCO X|VPOS": 10}}})
        branches = [
            {"store_id": "st_a373", "name": "A", "box_count": 3, "medios": [{"bank_name": "BANCO X", "product_name": "VPOS"}]},
            {"store_id": "st_b373", "name": "B", "box_count": 1, "medios": [{"bank_name": "BANCO X", "product_name": "VPOS"}]},
            {"name": "TEST_C nueva", "box_count": 4, "medios": [{"bank_name": "BANCO X", "product_name": "VPOS"}]},
        ]
        r = admin.put(f"{BASE_URL}/api/projects/{pid}/master-override", json={"branches": branches})
        assert r.status_code == 200, r.text
        rp = r.json().get("rollup_progress")
        assert rp is not None
        # weighted: 3*100 / (3+1+4) = 37.5
        assert rp["global_progress"] == 37.5, rp
        assert _get(pid)["rollup_progress"]["global_progress"] == 37.5

    def test_non_admin_forbidden(self):
        s = _login(*CORP)
        r = s.put(f"{BASE_URL}/api/projects/prj_nonexistent/master-override", json={})
        assert r.status_code == 403


# ---- (D) Cobro recurrente on direct projects ----
class TestCobro:
    def test_corp_user_toggles_direct_project(self):
        pid = _mk("En Gestión", extra={"origin": "direct", "client_segment": "CORP", "cobro_recurrente_status": False})
        s = _login(*CORP)
        r = s.put(f"{BASE_URL}/api/projects/{pid}/cobro-recurrente", json={})
        assert r.status_code == 200, r.text
        assert r.json()["cobro_recurrente_status"] is True
        p = _get(pid)
        assert p["cobro_recurrente_status"] is True and p["cobro_recurrente_at"] and p["cobro_recurrente_by"]
        assert any(n["text"] == "Se marcó cobro recurrente como cobrado (Proyecto Directo)." for n in p["notes"])
        r2 = s.put(f"{BASE_URL}/api/projects/{pid}/cobro-recurrente", json={})
        assert r2.status_code == 200 and r2.json()["cobro_recurrente_status"] is False
        assert any(n["text"] == "Se desmarcó el cobro recurrente (Proyecto Directo)." for n in _get(pid)["notes"])

    def test_pyme_user_forbidden_on_corp_direct(self):
        pid = _mk("En Gestión", extra={"origin": "direct", "client_segment": "CORP"})
        s = _login(*PYME)
        r = s.put(f"{BASE_URL}/api/projects/{pid}/cobro-recurrente", json={})
        assert r.status_code == 403

    def test_admin_toggles_direct(self, admin):
        pid = _mk("En Gestión", extra={"origin": "direct", "client_segment": "CORP"})
        r = admin.put(f"{BASE_URL}/api/projects/{pid}/cobro-recurrente", json={"status": True})
        assert r.status_code == 200 and r.json()["cobro_recurrente_status"] is True


# ---- (F) Quote history segmentation ----
def _suffixes(rows):
    return {(r.get("quote_number") or "").rsplit("-", 1)[-1].upper() for r in rows}


class TestQuoteHistory:
    def test_pyme_only_pyme(self):
        s = _login(*PYME)
        r = s.get(f"{BASE_URL}/api/quote-history")
        assert r.status_code == 200, r.text
        rows = r.json()
        assert rows and "CORP" not in _suffixes(rows), _suffixes(rows)

    def test_pyme_cannot_override_segment(self):
        s = _login(*PYME)
        rows = s.get(f"{BASE_URL}/api/quote-history", params={"segment": "CORP"}).json()
        assert "CORP" not in _suffixes(rows)

    def test_corp_only_corp(self):
        s = _login(*CORP)
        r = s.get(f"{BASE_URL}/api/quote-history")
        assert r.status_code == 200, r.text
        rows = r.json()
        assert rows and "PYME" not in _suffixes(rows), _suffixes(rows)

    def test_admin_all_and_filter(self, admin):
        allr = admin.get(f"{BASE_URL}/api/quote-history").json()
        corp = admin.get(f"{BASE_URL}/api/quote-history", params={"segment": "CORP"}).json()
        pyme = admin.get(f"{BASE_URL}/api/quote-history", params={"segment": "PYME"}).json()
        assert {"CORP", "PYME"} <= _suffixes(allr)
        assert "PYME" not in _suffixes(corp) and corp
        assert "CORP" not in _suffixes(pyme) and pyme
        assert len(corp) + len(pyme) == len(allr)
        print("counts all/corp/pyme", len(allr), len(corp), len(pyme))

    def test_corp_user_detail_of_pyme_record_forbidden(self, admin):
        pyme = admin.get(f"{BASE_URL}/api/quote-history", params={"segment": "PYME"}).json()
        hid = pyme[0]["history_id"]
        s = _login(*CORP)
        r = s.get(f"{BASE_URL}/api/quote-history/{hid}")
        assert r.status_code == 403, r.status_code
