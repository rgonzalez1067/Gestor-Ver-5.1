# Reporte de Seguimiento de Proyectos (GET /api/projects-report/followup + export pdf/xlsx). Read-only.
import io
import os
from datetime import datetime, timezone

import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
ADMIN = ("qa.integradores@megasoft.com.ve", "QaIntegr2026*Ok")
NONADMIN = ("kherrera@megasoft.com.ve", "Kherrera2026*Qa")
FINISHED = {"Culminado", "Implementado parcial", "Anulado", "Cancelado", "Finalizado"}


def _login(email, pwd):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={"email": email, "password": pwd}, timeout=60)
    if r.status_code != 200:
        pytest.skip(f"login failed {email}: {r.status_code} {r.text[:200]}")
    d = r.json()
    tok = d.get("session_token") or d.get("token") or d.get("access_token")
    if not tok:
        pytest.skip(f"no token for {email}: {d}")
    s = requests.Session()
    s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


@pytest.fixture(scope="module")
def admin():
    return _login(*ADMIN)


@pytest.fixture(scope="module")
def nonadmin():
    return _login(*NONADMIN)


@pytest.fixture(scope="module")
def admin_report(admin):
    r = admin.get(f"{BASE_URL}/api/projects-report/followup", timeout=120)
    assert r.status_code == 200, r.text[:300]
    return r.json()


@pytest.fixture(scope="module")
def admin_projects(admin):
    r = admin.get(f"{BASE_URL}/api/projects", timeout=120)
    assert r.status_code == 200
    return {p["project_id"]: p for p in r.json()}


@pytest.fixture(scope="module")
def sla_stages(admin):
    r = admin.get(f"{BASE_URL}/api/project-sla/config", timeout=60)
    return (r.json().get("config") or {}).get("stages") or {} if r.status_code == 200 else {}


def _ptype(qt):
    t = (qt or "").upper()
    return "LINK" if t in ("LINK_PAGO", "LINK") else "MPOS" if t == "FAST_TRACK" else t


def _sent(p):
    return str(p.get("sent_to_implementation_at") or p.get("created_at") or "")[:10]


def _ids(rep):
    return {r["project_id"] for r in rep["rows"]}


class TestFollowupBase:
    def test_unauth(self):
        r = requests.get(f"{BASE_URL}/api/projects-report/followup", timeout=60)
        assert r.status_code in (401, 403)

    def test_structure_and_count_vs_grid(self, admin_report, admin_projects):
        rows = admin_report["rows"]
        assert len(rows) > 0
        assert admin_report["kpis"]["total"] == len(rows)
        k = admin_report["kpis"]
        assert k["critico"] + k["medio"] + k["al_dia"] == k["total"]
        print("report rows", len(rows), "grid", len(admin_projects), "kpis", k)
        assert _ids(admin_report) == set(admin_projects.keys())
        for key in ("implementadores", "generadores", "estatus"):
            assert isinstance(admin_report["options"][key], list) and admin_report["options"][key]

    def test_sort_order(self, admin_report):
        order = {"critico": 0, "medio": 1, "al_dia": 2}
        keys = [(order[r["nivel"]], -r["dias_retraso"]) for r in admin_report["rows"]]
        assert keys == sorted(keys)

    def test_columns_vs_grid(self, admin_report, admin_projects, sla_stages):
        mism = []
        for r in admin_report["rows"]:
            p = admin_projects[r["project_id"]]
            exp_av = round(float((p.get("rollup_progress") or {}).get("global_progress") or 0))
            stage = "por_asignar" if not p.get("assigned_to_name") else "asignado" if not p.get("ticket_number") else "en_gestion"
            c = sla_stages.get(stage) or {}
            days = int(p.get("business_days_in_state") or 0)
            lvl = "al_dia" if p.get("status") in FINISHED else "critico" if days >= int(c.get("delay_days", 4)) \
                else "medio" if days >= int(c.get("warning_days", 2)) else "al_dia"
            checks = {
                "avance": (r["avance"], exp_av),
                "estado": (r["estado"], p.get("status", "")),
                "generador": (r["generador"], p.get("created_by_name", "")),
                "implementador": (r["implementador"], p.get("assigned_to_name") or "Sin asignar"),
                "nivel": (r["nivel"], lvl),
                "dias": (r["dias_retraso"], 0 if p.get("status") in FINISHED else days),
                "fecha_envio": (r["fecha_envio"], _sent(p)),
            }
            if p.get("assigned_to_name"):
                checks["asignacion"] = (str(r["fecha_asignacion"] or "")[:10], str(p.get("assigned_at") or "")[:10])
            for k, (a, b) in checks.items():
                if a != b:
                    mism.append((r["project_number"], k, a, b))
        print("mismatches", len(mism), mism[:15])
        assert not mism


class TestFollowupFilters:
    def test_filter_implementador(self, admin, admin_report, admin_projects):
        name = admin_report["options"]["implementadores"][0]
        rep = admin.get(f"{BASE_URL}/api/projects-report/followup", params={"implementador": name}, timeout=120).json()
        exp = {pid for pid, p in admin_projects.items() if p.get("assigned_to_name") == name}
        assert _ids(rep) == exp and len(exp) > 0

    def test_filter_generador(self, admin, admin_report, admin_projects):
        name = admin_report["options"]["generadores"][0]
        rep = admin.get(f"{BASE_URL}/api/projects-report/followup", params={"generador": name}, timeout=120).json()
        exp = {pid for pid, p in admin_projects.items() if p.get("created_by_name") == name}
        assert _ids(rep) == exp and len(exp) > 0

    @pytest.mark.parametrize("tipo", ["VPOS", "MPOS", "GATEWAY", "LINK"])
    def test_filter_tipo(self, admin, admin_projects, tipo):
        rep = admin.get(f"{BASE_URL}/api/projects-report/followup", params={"tipo": tipo}, timeout=120).json()
        exp = {pid for pid, p in admin_projects.items() if _ptype(p.get("quote_type")) == tipo}
        print(tipo, len(exp))
        assert _ids(rep) == exp

    def test_filter_estatus(self, admin, admin_report, admin_projects):
        for st in admin_report["options"]["estatus"][:3]:
            rep = admin.get(f"{BASE_URL}/api/projects-report/followup", params={"estatus": st}, timeout=120).json()
            exp = {pid for pid, p in admin_projects.items() if p.get("status") == st}
            assert _ids(rep) == exp, st
            assert all(r["estado"] == st for r in rep["rows"])

    def test_filter_date_range(self, admin, admin_projects):
        desde, hasta = "2026-08-01", "2026-09-30"
        rep = admin.get(f"{BASE_URL}/api/projects-report/followup", params={"desde": desde, "hasta": hasta}, timeout=120).json()
        exp = {pid for pid, p in admin_projects.items() if desde <= _sent(p) <= hasta}
        print("date range", len(exp))
        assert _ids(rep) == exp

    def test_combined_no_match(self, admin):
        rep = admin.get(f"{BASE_URL}/api/projects-report/followup", params={"implementador": "ZZZ_NOEXISTE"}, timeout=120).json()
        assert rep["rows"] == [] and rep["kpis"]["total"] == 0 and rep["kpis"]["avance_promedio"] == 0


class TestFollowupExport:
    def test_pdf(self, admin):
        r = admin.get(f"{BASE_URL}/api/projects-report/followup/export", params={"format": "pdf", "tipo": "VPOS"}, timeout=180)
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("application/pdf")
        assert r.content[:5] == b"%PDF-"

    def test_pdf_empty(self, admin):
        r = admin.get(f"{BASE_URL}/api/projects-report/followup/export", params={"format": "pdf", "implementador": "ZZZ"}, timeout=120)
        assert r.status_code == 200 and r.content[:5] == b"%PDF-"

    def test_xlsx_matches_rows(self, admin):
        from openpyxl import load_workbook
        params = {"tipo": "MPOS"}
        rep = admin.get(f"{BASE_URL}/api/projects-report/followup", params=params, timeout=120).json()
        r = admin.get(f"{BASE_URL}/api/projects-report/followup/export",
                      params={**params, "format": "xlsx", "filters_label": "Tipo: MPOS"}, timeout=180)
        assert r.status_code == 200
        assert "spreadsheetml" in r.headers["content-type"]
        ws = load_workbook(io.BytesIO(r.content)).active
        assert ws["A2"].value == "Filtros: Tipo: MPOS"
        data = [row for row in ws.iter_rows(min_row=6, values_only=True) if row[0]]
        assert len(data) == len(rep["rows"])
        assert [d[0] for d in data] == [x["project_number"] for x in rep["rows"]]
        assert [d[11] for d in data] == [x["nivel_label"] for x in rep["rows"]]

    def test_invalid_format(self, admin):
        r = admin.get(f"{BASE_URL}/api/projects-report/followup/export", params={"format": "csv"}, timeout=60)
        assert r.status_code == 400


class TestFollowupVisibility:
    def test_nonadmin_same_as_grid(self, nonadmin, admin_report):
        g = nonadmin.get(f"{BASE_URL}/api/projects", timeout=120)
        assert g.status_code == 200
        rep = nonadmin.get(f"{BASE_URL}/api/projects-report/followup", timeout=120)
        assert rep.status_code == 200
        grid_ids = {p["project_id"] for p in g.json()}
        print("kherrera grid", len(grid_ids), "report", len(rep.json()["rows"]), "admin", len(admin_report["rows"]))
        assert _ids(rep.json()) == grid_ids
        assert len(grid_ids) < len(admin_report["rows"])

    def test_nonadmin_export(self, nonadmin):
        r = nonadmin.get(f"{BASE_URL}/api/projects-report/followup/export", params={"format": "xlsx"}, timeout=120)
        assert r.status_code == 200 and r.content[:2] == b"PK"
