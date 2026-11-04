# Bancos: operational_status (DESA/SQA/Imple/Primer Prod/Producción) en products + regresión medios-pago
import os
import copy
import pytest
import requests

BASE_URL = os.environ.get('REACT_APP_BACKEND_URL').rstrip('/')
STATUSES = ["DESA", "SQA", "Imple", "Primer Prod", "Producción"]


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": "rgonzalez@megasoft.com.ve", "password": "Mega2026*"})
    if r.status_code != 200:
        pytest.skip("login failed")
    tok = r.json().get("session_token") or r.json().get("token")
    if tok:
        s.headers.update({"Authorization": f"Bearer {tok}"})
    return s


@pytest.fixture(scope="module")
def banks(client):
    r = client.get(f"{BASE_URL}/api/banks")
    assert r.status_code == 200
    return r.json()


def _bank_payload(bank):
    keys = ["name", "type", "country", "code", "logo_url", "contact_name", "contact_email", "contact_phone",
            "contacts", "products", "notes", "address", "website", "tipo_corp", "integrations", "is_active"]
    return {k: copy.deepcopy(v) for k, v in bank.items() if k not in ("_id", "bank_id", "created_at", "updated_at", "pipeline_products")}


class TestMigration:
    def test_all_products_have_status(self, banks):
        prods = [p for b in banks for p in (b.get("products") or [])]
        assert len(prods) > 0
        for p in prods:
            assert p.get("operational_status") in STATUSES, p
            assert p["pre_production"] == (p["operational_status"] != "Producción")

    def test_counts(self, banks):
        prods = [p for b in banks for p in (b.get("products") or [])]
        from collections import Counter
        c = Counter(p["operational_status"] for p in prods)
        print("STATUS COUNTS:", dict(c), "total", len(prods))
        assert c.get("Producción", 0) > 0


class TestPutStatus:
    def _pick(self, banks):
        for b in banks:
            if b.get("products"):
                return b
        pytest.skip("no bank with products")

    def test_put_sqa_and_produccion_and_legacy(self, client, banks):
        bank = self._pick(banks)
        bid = bank["bank_id"]
        orig = copy.deepcopy(bank["products"])
        payload = _bank_payload(bank)
        try:
            # SQA -> pre_production True
            payload["products"][0]["operational_status"] = "SQA"
            payload["products"][0]["pre_production"] = False  # inconsistente a propósito: status manda
            r = client.put(f"{BASE_URL}/api/banks/{bid}", json=payload)
            assert r.status_code == 200, r.text
            p0 = r.json()["products"][0]
            assert p0["operational_status"] == "SQA" and p0["pre_production"] is True
            g = client.get(f"{BASE_URL}/api/banks/{bid}/detail").json()["products"][0]
            assert g["operational_status"] == "SQA" and g["pre_production"] is True

            # Producción -> pre_production False
            payload["products"][0]["operational_status"] = "Producción"
            payload["products"][0]["pre_production"] = True
            r = client.put(f"{BASE_URL}/api/banks/{bid}", json=payload)
            p0 = r.json()["products"][0]
            assert p0["operational_status"] == "Producción" and p0["pre_production"] is False

            # Legacy: sin operational_status, pre_production True -> Imple
            payload["products"][0].pop("operational_status", None)
            payload["products"][0]["pre_production"] = True
            r = client.put(f"{BASE_URL}/api/banks/{bid}", json=payload)
            p0 = r.json()["products"][0]
            assert p0["operational_status"] == "Imple" and p0["pre_production"] is True

            # Legacy False -> Producción
            payload["products"][0].pop("operational_status", None)
            payload["products"][0]["pre_production"] = False
            r = client.put(f"{BASE_URL}/api/banks/{bid}", json=payload)
            p0 = r.json()["products"][0]
            assert p0["operational_status"] == "Producción" and p0["pre_production"] is False

            # Primer Prod
            payload["products"][0]["operational_status"] = "Primer Prod"
            r = client.put(f"{BASE_URL}/api/banks/{bid}", json=payload)
            assert r.json()["products"][0]["pre_production"] is True

            # inválido -> 422
            payload["products"][0]["operational_status"] = "XYZ"
            r = client.put(f"{BASE_URL}/api/banks/{bid}", json=payload)
            assert r.status_code == 422
        finally:
            payload["products"] = orig
            r = client.put(f"{BASE_URL}/api/banks/{bid}", json=payload)
            assert r.status_code == 200
            restored = client.get(f"{BASE_URL}/api/banks/{bid}/detail").json()["products"]
            assert [p["operational_status"] for p in restored] == [p["operational_status"] for p in orig]


class TestMediosPagoRegression:
    def test_medios_pago_excludes_preprod(self, client, banks):
        checked = 0
        for b in banks:
            prods = b.get("products") or []
            pre = {p["product_name"] for p in prods if p.get("operational_status") != "Producción"}
            if not pre:
                continue
            r = client.get(f"{BASE_URL}/api/banco-mediopago-condiciones/medios-pago", params={"bank_id": b["bank_id"]})
            assert r.status_code == 200, r.text
            data = r.json()
            items = data if isinstance(data, list) else data.get("items") or data.get("medios_pago") or []
            names = {(i.get("product_name") or i.get("name") or i.get("medio_pago")) if isinstance(i, dict) else i for i in items}
            assert not (names & pre), f"{b['name']}: {names & pre}"
            checked += 1
            if checked >= 5:
                break
        print("banks checked:", checked)
