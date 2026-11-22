# Ecosystem contacts (wizard) + add contacts to Reel Corporativo — iteration 388
import os
import pytest
import requests
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
BASE_URL = os.environ.get('TEST_BASE_URL', 'http://localhost:8001')
EMP = "emp_bbeb6f5908f2"
QA_EMAILS = ["qa.eco1@example.com", "qa.eco2@example.com"]


@pytest.fixture(scope="module")
def client():
    s = requests.Session()
    r = s.post(f"{BASE_URL}/api/auth/login", json={"email": "qa.integradores@megasoft.com.ve", "password": "QaIntegr2026*Ok"})
    if r.status_code != 200 or not r.json().get("session_token"):
        pytest.skip(f"login failed {r.status_code}")
    s.headers.update({"Authorization": f"Bearer {r.json()['session_token']}"})
    yield s
    # cleanup QA contacts added to Galac reel
    db = MongoClient(os.environ['MONGO_URL'])[os.environ['DB_NAME']]
    db.empresas_integradoras.update_one({"empresa_id": EMP}, {"$pull": {"contacts": {"full_name": {"$regex": "^QA "}}}})


# --- GET ecosystem-contacts
def test_ecosystem_contacts_galac(client):
    r = client.get(f"{BASE_URL}/api/integrator-companies/ecosystem-contacts", params={"empresa_id": EMP})
    assert r.status_code == 200
    data = r.json()
    names = [c["name"] for c in data]
    print(data)
    assert "Kevin Morillo" in names
    assert names.count("Kevin Morillo") == 1  # dedupe across corporate + app techs
    kev = next(c for c in data if c["name"] == "Kevin Morillo")
    assert kev["source"] == "Corporativo"
    assert any(c["source"].startswith("Técnico · ") for c in data)
    assert {"David Garcia", "Maria Barreto"} <= set(names)
    assert names == sorted(names, key=str.lower)
    keys = [(c["email"] or c["name"]).lower() for c in data]
    assert len(keys) == len(set(keys))


def test_ecosystem_contacts_unknown_empresa(client):
    r = client.get(f"{BASE_URL}/api/integrator-companies/ecosystem-contacts", params={"empresa_id": "emp_nope"})
    assert r.status_code == 200 and r.json() == []


def test_ecosystem_contacts_requires_auth():
    r = requests.get(f"{BASE_URL}/api/integrator-companies/ecosystem-contacts", params={"empresa_id": EMP})
    assert r.status_code == 401


def test_ecosystem_contacts_missing_param(client):
    r = client.get(f"{BASE_URL}/api/integrator-companies/ecosystem-contacts")
    assert r.status_code == 422


# --- POST add contacts to reel
def test_add_contacts_dedupe_and_invalid(client):
    payload = {"contacts": [
        {"full_name": "QA Eco Uno", "email": QA_EMAILS[0], "phone": "0414-1111111", "role": "Dev"},
        {"full_name": "QA Eco Uno Dup", "email": QA_EMAILS[0].upper()},  # dup email
        {"full_name": "QA Eco Bad", "email": "not-an-email"},  # invalid
        {"full_name": "   ", "email": "x@y.com"},  # empty name
        {"full_name": "QA Eco Dos", "email": QA_EMAILS[1]},
    ]}
    r = client.post(f"{BASE_URL}/api/integrator-companies/{EMP}/contacts", json=payload)
    assert r.status_code == 200, r.text
    assert r.json() == {"added": 2}
    g = client.get(f"{BASE_URL}/api/integrator-companies/{EMP}")
    assert g.status_code == 200
    contacts = g.json()["contacts"]
    emails = [c.get("email") for c in contacts]
    assert QA_EMAILS[0] in emails and QA_EMAILS[1] in emails
    assert not any(c["full_name"] == "QA Eco Bad" for c in contacts)
    assert contacts[0]["full_name"] == "Kevin Morillo"  # principal untouched
    # repeat → 0 added
    r2 = client.post(f"{BASE_URL}/api/integrator-companies/{EMP}/contacts", json=payload)
    assert r2.json() == {"added": 0}
    # ecosystem now includes them as Corporativo
    eco = client.get(f"{BASE_URL}/api/integrator-companies/ecosystem-contacts", params={"empresa_id": EMP}).json()
    assert any(c["name"] == "QA Eco Uno" and c["source"] == "Corporativo" for c in eco)


def test_add_contacts_404(client):
    r = client.post(f"{BASE_URL}/api/integrator-companies/emp_nope/contacts", json={"contacts": [{"full_name": "QA X"}]})
    assert r.status_code == 404


def test_add_contacts_requires_auth():
    r = requests.post(f"{BASE_URL}/api/integrator-companies/{EMP}/contacts", json={"contacts": []})
    assert r.status_code in (401, 403)


# --- Known gap: a name-only contact whose name matches an existing contact WITH email is not deduped
def test_add_contacts_dedupe_name_only_vs_existing_email(client):
    client.post(f"{BASE_URL}/api/integrator-companies/{EMP}/contacts", json={"contacts": [{"full_name": "QA Eco Tres", "email": "qa.eco3@example.com"}]})
    r = client.post(f"{BASE_URL}/api/integrator-companies/{EMP}/contacts", json={"contacts": [{"full_name": "QA Eco Tres", "email": ""}]})
    assert r.json() == {"added": 0}, "name-only duplicate of existing contact was added"
