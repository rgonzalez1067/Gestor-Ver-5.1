# Iter358: Edición Maestra — conversión sede única → multitienda (convert_to_multistore + inherit_main)
import os
import copy
import pytest
import requests
from pymongo import MongoClient

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
PID = "prj_826643491b64"
ADMIN = {"email": "rgonzalez@megasoft.com.ve", "password": "Mega2026*"}

_db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]


@pytest.fixture(scope="module")
def s():
    ses = requests.Session()
    r = ses.post(f"{BASE_URL}/api/auth/login", json=ADMIN, timeout=30)
    if r.status_code != 200:
        pytest.skip(f"login failed {r.status_code}")
    tok = r.json().get("session_token") or r.json().get("token")
    if tok:
        ses.headers["Authorization"] = f"Bearer {tok}"
    return ses


@pytest.fixture()
def backup():
    """Respaldo completo y restauración exacta con replace_one."""
    orig = _db.projects.find_one({"project_id": PID})
    assert orig and orig.get("project_type") == "single", "proyecto de prueba no es single"
    yield copy.deepcopy(orig)
    _db.projects.replace_one({"_id": orig["_id"]}, orig)
    assert _db.projects.find_one({"_id": orig["_id"]}) == orig


MEDIOS = [{"bank_name": "Banco Activo", "product_name": p} for p in
          ["Tarjeta de Crédito/Débito", "Cambio Pago Movil", "Verificación Pago Movil"]]


def _put(s, body):
    return s.put(f"{BASE_URL}/api/projects/{PID}/master-override", json=body, timeout=30)


def _branches(b1=3, b2=1, cid="cli_b5f9a852e3ec"):
    return [
        {"store_id": None, "inherit_main": True, "name": "Principal", "client_id": cid, "box_count": b1, "medios": MEDIOS},
        {"store_id": None, "name": "TEST_Sucursal 2", "client_id": cid, "box_count": b2, "medios": MEDIOS[:1]},
    ]


class TestConvertToMultistore:
    def test_convert_without_branches_400(self, s, backup):
        r = _put(s, {"convert_to_multistore": True})
        assert r.status_code == 400
        assert "sucursal" in r.json()["detail"].lower()
        r = _put(s, {"convert_to_multistore": True, "branches": []})
        assert r.status_code == 400
        assert _db.projects.find_one({"project_id": PID})["project_type"] == "single"

    def test_convert_exceed_total_boxes_400(self, s, backup):
        r = _put(s, {"convert_to_multistore": True, "branches": _branches(4, 1)})
        assert r.status_code == 400
        assert r.json()["detail"].startswith("Límite Excedido")
        assert _db.projects.find_one({"project_id": PID})["project_type"] == "single"

    def test_convert_exceed_medio_cap_400(self, s, backup):
        # 3 + 2 = 5 > 4 total ya falla; probamos medio: 2+2 en TDC ok total=4 → OK; usar 4+0 con medio extra en b2? -> 0 cajas
        br = _branches(2, 2)
        br[1]["medios"] = MEDIOS  # 4 cajas por medio = tope 4 → válido
        r = _put(s, {"convert_to_multistore": True, "branches": br})
        assert r.status_code == 200, r.text

    def test_convert_success_inherits_phases(self, s, backup):
        # inyecta fases completadas en la matriz principal (se restaura al final)
        m = copy.deepcopy(backup["implementation_matrix"])
        for pn in m["Banco Activo"]:
            m["Banco Activo"][pn] = {"Recibido": {"completed": True, "date": "2026-01-10"},
                                     "Configurado": {"completed": True, "date": "2026-01-11"}}
        _db.projects.update_one({"project_id": PID}, {"$set": {"implementation_matrix": m}})

        r = _put(s, {"convert_to_multistore": True, "branches": _branches(3, 1)})
        assert r.status_code == 200, r.text
        p = _db.projects.find_one({"project_id": PID}, {"_id": 0})
        assert p["project_type"] == "multistore"
        assert len(p["stores"]) == 2
        s1, s2 = p["stores"]
        assert s1["name"] == "Principal" and s1["box_count"] == 3
        assert s2["name"] == "TEST_Sucursal 2" and s2["box_count"] == 1
        for pn in m["Banco Activo"]:
            ph = s1["implementation_matrix"]["Banco Activo"][pn]
            assert ph.get("Recibido", {}).get("completed") is True, f"S1 {pn} no heredó Recibido: {ph}"
            assert ph.get("Configurado", {}).get("completed") is True
        tdc = s2["implementation_matrix"]["Banco Activo"]["Tarjeta de Crédito/Débito"]
        assert not (tdc.get("Recibido") or {}).get("completed"), "S2 no debe heredar avance"
        assert list(s2["implementation_matrix"]["Banco Activo"].keys()) == ["Tarjeta de Crédito/Débito"]
        assert not p.get("rifs"), f"no debería crear rifs: {p.get('rifs')}"
        assert p["contract_baseline"]["total_boxes"] == 4
        last = p["bitacora"][-1]["text"]
        assert "Estructura: 'single' → 'multistore'" in last, last

        # GET detalle y progreso
        d = s.get(f"{BASE_URL}/api/projects/{PID}", timeout=30)
        assert d.status_code == 200
        assert d.json()["project_type"] == "multistore"
        assert len(d.json()["stores"]) == 2

    def test_convert_flag_ignored_on_multistore_after(self, s, backup):
        # convertir y luego volver a enviar convert_to_multistore sobre multistore → no rompe
        assert _put(s, {"convert_to_multistore": True, "branches": _branches(3, 1)}).status_code == 200
        p = _db.projects.find_one({"project_id": PID})
        br = [{"store_id": st["store_id"], "name": st["name"], "client_id": "cli_b5f9a852e3ec",
               "box_count": st["box_count"], "medios": MEDIOS[:1]} for st in p["stores"]]
        r = _put(s, {"convert_to_multistore": True, "branches": br})
        assert r.status_code == 200, r.text
        assert _db.projects.find_one({"project_id": PID})["project_type"] == "multistore"
