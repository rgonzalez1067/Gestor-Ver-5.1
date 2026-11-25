# Iter401: Contacto Inicial - adjunto de respaldo (imagen / .eml): stage, create, download, email preview, replace, delete, audit.
import io
import os
import struct
import zlib
import pytest
import requests

BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
API = f"{BASE_URL}/api"
ADMIN = {"email": "qa.integradores@megasoft.com.ve", "password": "QaIntegr2026*Ok"}

EML_BYTES = (
    b"From: TEST Remitente <test.from@example.com>\r\n"
    b"To: TEST Destino <test.to@example.com>\r\n"
    b"Subject: TEST_Asunto respaldo contacto\r\n"
    b"Date: Mon, 12 Jan 2026 10:00:00 -0400\r\n"
    b"MIME-Version: 1.0\r\n"
    b"Content-Type: text/plain; charset=utf-8\r\n\r\n"
    b"Cuerpo TEST_ del correo de respaldo.\r\n"
)


def make_png():
    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    raw = b"".join(b"\x00" + b"\xff\x00\x00" * 4 for _ in range(4))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 4, 4, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


PNG_BYTES = make_png()


@pytest.fixture(scope="module")
def s():
    r = requests.post(f"{API}/auth/login", json=ADMIN)
    if r.status_code != 200:
        pytest.skip(f"login failed {r.status_code} {r.text[:200]}")
    tok = r.json().get("session_token") or r.json().get("token")
    sess = requests.Session()
    sess.headers.update({"Authorization": f"Bearer {tok}"})
    return sess


@pytest.fixture(scope="module")
def created(s):
    ids = []
    yield ids
    for cid in ids:
        s.delete(f"{API}/initial-contacts/{cid}")


def stage(s, name, data, ctype):
    return s.post(f"{API}/initial-contacts/attachments/stage", files={"file": (name, io.BytesIO(data), ctype)})


def create_contact(s, created, suffix, staged_id=None):
    payload = {"contact_name": f"TEST_Contacto {suffix}", "legal_name": f"TEST_Empresa {suffix}", "phone": "04140000000",
               "email": "", "interest_notes": "TEST", "staged_attachment_id": staged_id}
    r = s.post(f"{API}/initial-contacts", json=payload)
    assert r.status_code == 200, r.text
    c = r.json()
    created.append(c["contact_id"])
    return c


def get_contact(s, cid):
    lst = s.get(f"{API}/initial-contacts").json()
    return next((c for c in lst if c["contact_id"] == cid), None)


class TestStageValidation:
    def test_reject_exe(self, s):
        r = stage(s, "TEST_malo.exe", b"MZ\x00\x00", "application/octet-stream")
        assert r.status_code == 400
        assert "Formato no permitido" in r.json()["detail"]

    def test_reject_xlsx_zip(self, s):
        for n, ct in [("TEST_a.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"), ("TEST_a.zip", "application/zip")]:
            r = stage(s, n, b"PK\x03\x04data", ct)
            assert r.status_code == 400, n

    def test_reject_over_10mb(self, s):
        r = stage(s, "TEST_big.png", b"\x00" * (10 * 1024 * 1024 + 10), "image/png")
        assert r.status_code == 400
        assert "10 MB" in r.json()["detail"]

    def test_reject_spoofed_ctype(self, s):
        r = stage(s, "TEST_x.png", PNG_BYTES, "application/x-msdownload")
        assert r.status_code == 400

    def test_bad_staged_id(self, s):
        r = s.post(f"{API}/initial-contacts", json={"contact_name": "TEST_x", "legal_name": "TEST_x", "phone": "1", "staged_attachment_id": "stg_nope"})
        assert r.status_code == 400

    def test_unauth(self):
        r = requests.post(f"{API}/initial-contacts/attachments/stage", files={"file": ("a.png", PNG_BYTES, "image/png")})
        assert r.status_code in (401, 403)


class TestImageFlow:
    def test_create_with_image_and_download(self, s, created):
        r = stage(s, "TEST_captura.png", PNG_BYTES, "image/png")
        assert r.status_code == 200, r.text
        st = r.json()
        assert st["adjunto_tipo"] == "IMAGEN" and st["staged_id"].startswith("stg_")
        c = create_contact(s, created, "img", st["staged_id"])
        assert c["adjunto_tipo"] == "IMAGEN"
        assert c["adjunto_nombre_original"] == "TEST_captura.png"
        assert c["adjunto_size"] == len(PNG_BYTES)
        listed = get_contact(s, c["contact_id"])
        assert listed["adjunto_tipo"] == "IMAGEN"
        d = s.get(f"{API}/initial-contacts/{c['contact_id']}/attachment")
        assert d.status_code == 200
        assert d.content == PNG_BYTES
        assert d.headers["content-type"].startswith("image/png")
        assert "attachment" in d.headers["content-disposition"] and "TEST_captura.png" in d.headers["content-disposition"]
        di = s.get(f"{API}/initial-contacts/{c['contact_id']}/attachment?inline=true")
        assert di.headers["content-disposition"].startswith("inline")
        # staged id is single-use
        r2 = s.post(f"{API}/initial-contacts", json={"contact_name": "TEST_x", "legal_name": "TEST_x", "phone": "1", "staged_attachment_id": st["staged_id"]})
        assert r2.status_code == 400
        # email preview on an image -> 400
        assert s.get(f"{API}/initial-contacts/{c['contact_id']}/attachment/email").status_code == 400
        pytest.img_contact = c["contact_id"]

    def test_audit_create_has_attachment(self, s):
        cid = pytest.img_contact
        r = s.get(f"{API}/audit-trails", params={"registro": cid, "action": "CREATE"})
        assert r.status_code == 200, r.text
        items = [i for i in r.json()["items"] if i.get("entidad") == "initial_contacts"]
        assert items, "no CREATE audit for contact"
        assert "adjunto_nombre_original" in items[0]["campos_modificados"]
        assert "adjunto_url" in items[0]["campos_modificados"]
        det = s.get(f"{API}/audit-trails/{items[0]['id']}").json()
        assert det["valores_nuevos"]["adjunto_nombre_original"] == "TEST_captura.png"

    def test_replace_with_eml_then_delete(self, s):
        cid = pytest.img_contact
        r = s.post(f"{API}/initial-contacts/{cid}/attachment", files={"file": ("TEST_reemplazo.eml", io.BytesIO(EML_BYTES), "message/rfc822")})
        assert r.status_code == 200, r.text
        assert r.json()["adjunto_tipo"] == "EML"
        c = get_contact(s, cid)
        assert c["adjunto_nombre_original"] == "TEST_reemplazo.eml"
        assert any("reemplazó" in b["description"] for b in c.get("bitacora", []))
        upd = s.get(f"{API}/audit-trails", params={"registro": cid, "action": "UPDATE"}).json()["items"]
        assert any("adjunto_nombre_original" in (i.get("campos_modificados") or []) for i in upd)
        d = s.delete(f"{API}/initial-contacts/{cid}/attachment")
        assert d.status_code == 200
        c = get_contact(s, cid)
        assert not c.get("adjunto_tipo")
        assert any("eliminó el documento" in b["description"] for b in c.get("bitacora", []))
        assert s.get(f"{API}/initial-contacts/{cid}/attachment").status_code == 404
        assert s.delete(f"{API}/initial-contacts/{cid}/attachment").status_code == 404


class TestEmlFlow:
    def test_create_with_eml_preview_and_bytes(self, s, created):
        st = stage(s, "TEST_correo.eml", EML_BYTES, "message/rfc822").json()
        assert st["adjunto_tipo"] == "EML"
        c = create_contact(s, created, "eml", st["staged_id"])
        cid = c["contact_id"]
        p = s.get(f"{API}/initial-contacts/{cid}/attachment/email")
        assert p.status_code == 200, p.text
        m = p.json()
        assert "test.from@example.com" in m["from"]
        assert "test.to@example.com" in m["to"]
        assert m["subject"] == "TEST_Asunto respaldo contacto"
        assert m["date"]
        assert "Cuerpo TEST_" in (m.get("text") or "")
        d = s.get(f"{API}/initial-contacts/{cid}/attachment")
        assert d.content == EML_BYTES
        assert ".eml" in d.headers["content-disposition"]

    def test_eml_octet_stream_accepted(self, s, created):
        r = stage(s, "TEST_b.eml", EML_BYTES, "application/octet-stream")
        assert r.status_code == 200
        create_contact(s, created, "eml2", r.json()["staged_id"])  # consume staged record so nothing is left behind


class TestNoAttachment:
    def test_create_without_attachment(self, s, created):
        c = create_contact(s, created, "noatt")
        assert not c.get("adjunto_tipo")
        assert s.get(f"{API}/initial-contacts/{c['contact_id']}/attachment").status_code == 404

    def test_upload_404_contact(self, s):
        r = s.post(f"{API}/initial-contacts/ic_doesnotexist/attachment", files={"file": ("a.png", io.BytesIO(PNG_BYTES), "image/png")})
        assert r.status_code == 404
