# Economic group PDF export: single top-left logo regression (bug: stretched logo in body)
import os
import pytest
import requests
import fitz

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": "rgonzalez@megasoft.com.ve", "password": "MegaSoft2026*"})
    if r.status_code != 200:
        pytest.skip(f"login failed {r.status_code} {r.text[:200]}")
    d = r.json()
    tok = d.get("session_token") or d.get("token")
    if not tok:
        pytest.skip(f"no token: {d}")
    s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


@pytest.fixture(scope="module")
def groups(client):
    r = client.get(f"{BASE_URL}/api/grupos-economicos")
    assert r.status_code == 200, r.text[:200]
    data = r.json()
    items = data if isinstance(data, list) else (data.get("items") or data.get("groups") or [])
    assert items, "no groups"
    # include the group with most clients
    items = sorted(items, key=lambda g: -(g.get("client_count") or g.get("rif_count") or 0))
    return items[:6]


def test_pdf_logo_top_left(client, groups):
    for g in groups:
        r = client.get(f"{BASE_URL}/api/grupos-economicos/{g['group_id']}/export-pdf")
        assert r.status_code == 200, (g["group_id"], r.status_code)
        assert r.headers["content-type"].startswith("application/pdf")
        doc = fitz.open(stream=r.content, filetype="pdf")
        text = doc[0].get_text()
        assert f"Grupo Económico: {g['name']}" in text or "Grupo Económico:" in text
        for h in ("Nombre de Fantasía", "RIF", "Nombre Jurídico"):
            assert h in text
        print(g["name"], "pages", doc.page_count)
        for p in doc:
            infos = p.get_image_info()
            print("  page", p.number + 1, [tuple(round(v, 1) for v in i["bbox"]) for i in infos])
            assert len(infos) == 1, f"page {p.number+1} has {len(infos)} images"
            x0, y0, x1, y1 = infos[0]["bbox"]
            assert x0 < 70 and y1 < 60, infos[0]["bbox"]
            assert (x1 - x0) <= 85 and (y1 - y0) <= 35


def test_pdf_404(client):
    r = client.get(f"{BASE_URL}/api/grupos-economicos/nonexistent_xyz/export-pdf")
    assert r.status_code == 404
