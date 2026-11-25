# Taller Audit report (/api/reports/taller-audit + export) regression tests with TEST_AUD_ data
import os, io, uuid, asyncio
import pytest, requests
from openpyxl import load_workbook
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('/app/frontend/.env')
load_dotenv('/app/backend/.env')
BASE_URL = os.environ['REACT_APP_BACKEND_URL'].rstrip('/')
mdb = MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
TAG = uuid.uuid4().hex[:6].upper()
PFX = f"TEST_AUD_{TAG}_"
CLIENT = f"TEST_AUD_CLIENT_{TAG}"

# (key, equipo estatus, quote status or None, archived, in_history, expected nivel, expected diag substring)
CASES = [
    ("REC_OK", "Recibido", None, False, False, "OK", "OK - Equipo recibido pendiente por cotizar"),
    ("REC_ALERT", "Recibido", "Borrador", False, False, "ALERTA", "ALERTA"),
    ("COT_OK", "Cotizado", "Enviada", False, False, "OK", "OK - Estatus alineado con cotización"),
    ("REP_OK", "En reparación", "Aprobada", False, False, "OK", "OK - Estatus alineado con cotización"),
    ("RPD_OK", "Reparado", "Facturada", False, False, "OK", "OK - Estatus alineado con cotización"),
    ("PAG_OK", "Pagado", "Pagada", False, False, "OK", "OK - Estatus alineado con cotización"),
    ("ENT_OK_ARCH", "Entregado", "Entregada", True, False, "OK", "OK - Estatus alineado con cotización"),
    ("ENT_OK_HIST", "Entregado", "Entregada", False, True, "OK", "OK - Estatus alineado con cotización"),
    ("ENT_BAD", "Entregado", "Pagada", False, False, "INCONSISTENCIA",
     "INCONSISTENCIA: Equipo en estatus Entregada pero su cotización aún no ha sido movida al Histórico."),
    ("REP_BAD", "En reparación", "Enviada", False, False, "INCONSISTENCIA",
     "INCONSISTENCIA: Equipo en estatus En reparación requiere cotización en Aprobada, pero figura en Enviada."),
    ("COT_NOQ", "Cotizado", None, False, False, "INCONSISTENCIA",
     "INCONSISTENCIA: Equipo en estatus Cotizado no posee cotización registrada."),
    ("PAG_NOQ", "Pagado", None, False, False, "INCONSISTENCIA",
     "INCONSISTENCIA: Equipo en estatus Pagada no posee cotización registrada."),
]


def login(email, pw):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": pw})
    assert r.status_code == 200, r.text
    d = r.json()
    tok = d.get("session_token") or d.get("token")
    assert tok, d
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(scope="module")
def admin():
    return login("qa.integradores@megasoft.com.ve", "QaIntegr2026*Ok")


@pytest.fixture(scope="module", autouse=True)
def seed():
    eq_ids, q_ids, h_ids = [], [], []
    for i, (k, est, qs, arch, hist, *_r) in enumerate(CASES):
        tid = f"te_{PFX}{k}"
        doc = {"taller_equipo_id": tid, "serial": f"{PFX}{k}", "modelo": "TEST model", "client_id": None,
               "client_name": CLIENT, "estatus": est,
               "fecha_ingreso": "2020-01-%02dT10:00:00+00:00" % (i + 1),
               "created_at": "2020-01-01T00:00:00+00:00", "updated_at": "2020-02-%02dT10:00:00+00:00" % (i + 1)}
        if qs:
            qid, qn = f"quo_{PFX}{k}", f"TEST_COT_{PFX}{k}"
            doc.update(quote_id=qid, quote_number=qn)
            if hist:
                mdb.quote_history.insert_one({"quote_id": qid, "quote_number": qn, "quote_status_final": qs, "TEST": True})
                h_ids.append(qid)
            else:
                mdb.quotes.insert_one({"quote_id": qid, "quote_number": qn, "quote_status": qs, "archived": arch,
                                       "client_name": CLIENT, "TEST": True})
                q_ids.append(qid)
        mdb.taller_equipos.insert_one(doc)
        eq_ids.append(tid)
    yield
    mdb.taller_equipos.delete_many({"taller_equipo_id": {"$in": eq_ids}})
    mdb.quotes.delete_many({"quote_id": {"$in": q_ids}})
    mdb.quote_history.delete_many({"quote_id": {"$in": h_ids}})


def get(h, **p):
    r = requests.get(f"{BASE_URL}/api/reports/taller-audit", headers=h, params=p, timeout=60)
    assert r.status_code == 200, r.text
    return r.json()


class TestAudit:
    def test_all_cases_diagnosis(self, admin):
        d = get(admin, resultado="todos", q=PFX)
        rows = {r["serial"]: r for r in d["rows"]}
        assert len(rows) == len(CASES)
        for k, est, qs, arch, hist, nivel, diag in CASES:
            r = rows[f"{PFX}{k}"]
            assert r["nivel"] == nivel, (k, r)
            assert diag in r["diagnostico"], (k, r["diagnostico"])
        assert d["kpis"] == {"total": 12, "consistentes": 7, "inconsistencias": 4, "alertas": 1}

    def test_resultado_filters(self, admin):
        inc = get(admin, resultado="inconsistencias", q=PFX)["rows"]
        assert len(inc) == 5 and all(r["nivel"] != "OK" for r in inc)
        ok = get(admin, resultado="consistentes", q=PFX)["rows"]
        assert len(ok) == 7 and all(r["nivel"] == "OK" for r in ok)
        default = get(admin, q=PFX)["rows"]
        assert len(default) == 5

    def test_estatus_filter(self, admin):
        rows = get(admin, resultado="todos", q=PFX, estatus="Entregado")["rows"]
        assert len(rows) == 3 and all(r["estatus"] == "Entregada" for r in rows)
        rows = get(admin, resultado="todos", q=PFX, estatus="Pagado")["rows"]
        assert len(rows) == 2

    def test_q_client(self, admin):
        rows = get(admin, resultado="todos", q=CLIENT.lower())["rows"]
        assert len(rows) == 12

    def test_dates(self, admin):
        rows = get(admin, resultado="todos", q=PFX, desde="2020-01-03", hasta="2020-01-05")["rows"]
        assert len(rows) == 3
        rows = get(admin, resultado="todos", q=PFX, desde="2020-02-01", hasta="2020-02-02", fecha_campo="actualizacion")["rows"]
        assert len(rows) == 2

    def test_export_matches(self, admin):
        p = {"resultado": "inconsistencias", "q": PFX}
        screen = get(admin, **p)["rows"]
        r = requests.get(f"{BASE_URL}/api/reports/taller-audit/export", headers=admin, params=p, timeout=60)
        assert r.status_code == 200
        assert "spreadsheetml" in r.headers["content-type"]
        ws = load_workbook(io.BytesIO(r.content)).active
        data = [row for row in ws.iter_rows(min_row=5, values_only=True) if row[0]]
        assert [x[0] for x in data] == [s["serial"] for s in screen]
        assert [x[9] for x in data] == [s["diagnostico"] for s in screen]

    def test_real_data_kpis(self, admin):
        d = get(admin, resultado="todos")
        k = d["kpis"]
        assert k["total"] == k["consistentes"] + k["inconsistencias"] + k["alertas"]
        print("REAL KPIS (incl TEST rows):", k)

    def test_non_admin_forbidden(self):
        h = login(os.environ.get("AUD_NONADMIN_EMAIL","kherrera@megasoft.com.ve"), os.environ.get("AUD_NONADMIN_PW","Kherrera2026*Qa"))
        assert requests.get(f"{BASE_URL}/api/reports/taller-audit", headers=h).status_code == 403
        assert requests.get(f"{BASE_URL}/api/reports/taller-audit/export", headers=h).status_code == 403

    def test_unauth(self):
        assert requests.get(f"{BASE_URL}/api/reports/taller-audit").status_code in (401, 403)
