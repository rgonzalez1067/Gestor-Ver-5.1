"""Políticas de seguridad: complejidad, historial, vencimiento, bloqueo por
intentos fallidos y 2FA por correo. Configuración global en db.security_policies."""
import hashlib
import re
import secrets
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException

from config import db, verify_password

POLICY_ID = "global"
DEFAULTS = {
    "password_max_age_days": 90,
    "expiry_warning_days": 7,
    "password_history_count": 5,
    "max_failed_attempts": 5,
    "lockout_minutes": 15,
    "two_factor_enabled": False,
    "min_password_length": 12,
    "otp_ttl_minutes": 10,
}
LIMITS = {
    "password_max_age_days": (1, 3650),
    "expiry_warning_days": (0, 365),
    "password_history_count": (0, 24),
    "max_failed_attempts": (1, 20),
    "lockout_minutes": (1, 1440),
    "min_password_length": (12, 128),
    "otp_ttl_minutes": (1, 60),
}
LABELS = {
    "password_max_age_days": "Vigencia de contraseñas",
    "expiry_warning_days": "Aviso previo de vencimiento",
    "password_history_count": "Historial de contraseñas",
    "max_failed_attempts": "Intentos fallidos permitidos",
    "lockout_minutes": "Duración del bloqueo",
    "min_password_length": "Longitud mínima de contraseña",
    "otp_ttl_minutes": "Vigencia del código 2FA",
}
SPECIAL_RE = r"[!@#$%^&*(),.?\":{}|<>\-_=+\[\]\\/;'`~]"


def _now():
    return datetime.now(timezone.utc)


def _parse(iso):
    if not iso:
        return None
    try:
        d = datetime.fromisoformat(str(iso))
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:
        return None


async def get_policy() -> dict:
    doc = await db.security_policies.find_one({"policy_id": POLICY_ID}, {"_id": 0}) or {}
    return {**DEFAULTS, **{k: doc[k] for k in DEFAULTS if k in doc}}


def clean_policy(data: dict) -> dict:
    out = {}
    for k, v in data.items():
        if k not in DEFAULTS:
            continue
        if k == "two_factor_enabled":
            out[k] = bool(v)
            continue
        try:
            n = int(v)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail=f"Valor inválido para {LABELS[k]}.")
        lo, hi = LIMITS[k]
        if not lo <= n <= hi:
            raise HTTPException(status_code=400, detail=f"{LABELS[k]} debe estar entre {lo} y {hi}.")
        out[k] = n
    return out


async def ensure_initial_setup():
    """Crea la política por defecto y fuerza (una sola vez) el cambio de clave a todos."""
    doc = await db.security_policies.find_one({"policy_id": POLICY_ID})
    if not doc:
        await db.security_policies.insert_one({"policy_id": POLICY_ID, **DEFAULTS, "created_at": _now().isoformat()})
        doc = {}
    if not doc.get("force_change_applied"):
        await db.users.update_many({"password_hash": {"$exists": True}}, {"$set": {"must_change_password": True}})
        await db.security_policies.update_one({"policy_id": POLICY_ID}, {"$set": {"force_change_applied": _now().isoformat()}})
    await db.user_password_history.create_index("user_id")
    await db.login_2fa_challenges.create_index("expires_at_dt", expireAfterSeconds=0)
    await db.password_change_tokens.create_index("expires_at_dt", expireAfterSeconds=0)


def password_errors(pwd: str, policy: dict) -> list:
    errs = []
    n = policy["min_password_length"]
    if len(pwd or "") < n:
        errs.append(f"al menos {n} caracteres")
    if not re.search(r"[A-Z]", pwd or ""):
        errs.append("una letra mayúscula")
    if not re.search(r"[a-z]", pwd or ""):
        errs.append("una letra minúscula")
    if not re.search(r"\d", pwd or ""):
        errs.append("un número")
    if not re.search(SPECIAL_RE, pwd or ""):
        errs.append("un carácter especial (!@#$%^&*(),.?\":{}|<>)")
    return errs


async def validate_new_password(user_id: str, current_hash: str, pwd: str):
    """Complejidad + reúso contra la clave actual y las últimas N del historial."""
    policy = await get_policy()
    errs = password_errors(pwd, policy)
    if errs:
        raise HTTPException(status_code=400, detail="Contraseña Inválida: debe tener " + ", ".join(errs) + ".")
    n = policy["password_history_count"]
    if n <= 0:
        return
    hashes = [current_hash] if current_hash else []
    hist = await db.user_password_history.find({"user_id": user_id}, {"_id": 0, "password_hash": 1}).sort("created_at", -1).to_list(n)
    hashes += [h["password_hash"] for h in hist]
    if any(verify_password(pwd, h) for h in hashes[:n]):
        raise HTTPException(status_code=400, detail=f"Contraseña Inválida: No puede utilizar ninguna de sus últimas {n} contraseñas anteriores.")


async def record_password_change(user_id: str, old_hash: str, new_hash: str):
    if old_hash:
        await db.user_password_history.insert_one({"user_id": user_id, "password_hash": old_hash, "created_at": _now().isoformat()})
        keep = max((await get_policy())["password_history_count"], 1)
        old = await db.user_password_history.find({"user_id": user_id}, {"_id": 1}).sort("created_at", -1).skip(keep).to_list(1000)
        if old:
            await db.user_password_history.delete_many({"_id": {"$in": [o["_id"] for o in old]}})
    await db.users.update_one({"user_id": user_id}, {"$set": {
        "password_hash": new_hash, "password_changed_at": _now().isoformat(), "must_change_password": False,
        "account_status": "ACTIVE", "failed_login_attempts": 0,
    }})


# ---------- Bloqueo por intentos fallidos ----------

def _lock_message(minutes_left: int) -> str:
    return (f"Cuenta bloqueada temporalmente por intentos fallidos. Intente nuevamente en {minutes_left} "
            f"minutos o contacte al administrador.")


def effective_lock_status(user: dict, policy: dict) -> str:
    """Estado mostrado: un bloqueo cuyo tiempo ya expiró se reporta como ACTIVE."""
    if user.get("account_status") != "LOCKED":
        return user.get("account_status") or "ACTIVE"
    ts = _parse(user.get("lockout_timestamp"))
    if not ts or _now() - ts >= timedelta(minutes=policy["lockout_minutes"]):
        return "ACTIVE"
    return "LOCKED"


async def check_lock(user: dict, policy: dict):
    if user.get("account_status") != "LOCKED":
        return
    ts = _parse(user.get("lockout_timestamp"))
    elapsed = (_now() - ts) if ts else timedelta(days=9999)
    duration = timedelta(minutes=policy["lockout_minutes"])
    if elapsed >= duration:
        await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"account_status": "ACTIVE", "failed_login_attempts": 0}, "$unset": {"lockout_timestamp": ""}})
        user["account_status"] = "ACTIVE"
        user["failed_login_attempts"] = 0
        return
    left = max(1, int((duration - elapsed).total_seconds() // 60) + (1 if (duration - elapsed).total_seconds() % 60 else 0))
    raise HTTPException(status_code=423, detail=_lock_message(left))


async def register_failure(user: dict, policy: dict):
    doc = await db.users.find_one_and_update(
        {"user_id": user["user_id"]}, {"$inc": {"failed_login_attempts": 1}},
        projection={"_id": 0, "failed_login_attempts": 1}, return_document=True,
    )
    attempts = int((doc or {}).get("failed_login_attempts") or 1)
    if attempts >= policy["max_failed_attempts"]:
        await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"account_status": "LOCKED", "lockout_timestamp": _now().isoformat()}})
        raise HTTPException(status_code=423, detail=_lock_message(policy["lockout_minutes"]))
    left = policy["max_failed_attempts"] - attempts
    raise HTTPException(status_code=401, detail=f"Credenciales inválidas. Le quedan {left} intento(s) antes del bloqueo temporal.")


async def reset_failures(user: dict):
    if user.get("failed_login_attempts") or user.get("account_status") == "LOCKED":
        await db.users.update_one({"user_id": user["user_id"]}, {"$set": {"failed_login_attempts": 0, "account_status": "ACTIVE"}, "$unset": {"lockout_timestamp": ""}})


# ---------- Vencimiento ----------

def expiry_info(user: dict, policy: dict) -> dict:
    """{'expired': bool, 'days_left': int|None}"""
    if user.get("must_change_password"):
        return {"expired": True, "days_left": 0}
    changed = _parse(user.get("password_changed_at")) or _parse(user.get("created_at"))
    if not changed:
        return {"expired": True, "days_left": 0}
    expires = changed + timedelta(days=policy["password_max_age_days"])
    now = _now()
    if now >= expires:
        return {"expired": True, "days_left": 0}
    days_left = (expires - now).days + (1 if (expires - now).seconds else 0)
    warn = days_left <= policy["expiry_warning_days"]
    return {"expired": False, "days_left": days_left if warn else None}


async def create_change_token(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    exp = _now() + timedelta(minutes=15)
    await db.password_change_tokens.insert_one({"token": token, "user_id": user_id, "expires_at": exp.isoformat(), "expires_at_dt": exp})
    return token


# ---------- 2FA ----------

def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def mask_email(email: str) -> str:
    name, _, dom = (email or "").partition("@")
    return f"{name[:2]}{'*' * max(len(name) - 2, 1)}@{dom}"


async def create_2fa_challenge(user: dict, policy: dict) -> str:
    code = f"{secrets.randbelow(1_000_000):06d}"
    challenge_id = secrets.token_urlsafe(24)
    exp = _now() + timedelta(minutes=policy["otp_ttl_minutes"])
    await db.login_2fa_challenges.delete_many({"user_id": user["user_id"]})
    await db.login_2fa_challenges.insert_one({
        "challenge_id": challenge_id, "user_id": user["user_id"], "code_hash": _hash_code(code),
        "attempts": 0, "expires_at": exp.isoformat(), "expires_at_dt": exp, "created_at": _now().isoformat(),
    })
    await send_2fa_email(user, code, policy["otp_ttl_minutes"])
    return challenge_id


async def send_2fa_email(user: dict, code: str, ttl: int):
    from services.email_service import send_email
    html = f"""
    <div style="font-family:Arial,sans-serif;max-width:560px;margin:0 auto;padding:20px;">
      <div style="background:#003366;padding:18px;text-align:center;border-radius:8px 8px 0 0;">
        <h1 style="color:white;margin:0;font-size:20px;">Gestor MegaNexus</h1>
      </div>
      <div style="background:#f8fafc;padding:28px;border:1px solid #e2e8f0;border-top:none;border-radius:0 0 8px 8px;">
        <p style="color:#475569;">Hola <strong>{user.get('first_name') or user.get('name', '')}</strong>,</p>
        <p style="color:#475569;">Tu código de verificación para ingresar al Gestor es:</p>
        <div style="text-align:center;margin:22px 0;font-size:34px;letter-spacing:10px;font-weight:bold;color:#003366;">{code}</div>
        <p style="color:#94a3b8;font-size:13px;">El código vence en {ttl} minutos. Si no intentaste ingresar, cambia tu contraseña.</p>
      </div>
    </div>"""
    await send_email(to=[user["email"]], subject="Código de verificación — Gestor MegaNexus", html=html, action="login_2fa")
    # No dejar el código legible en el historial de correos.
    async for log in db.email_logs.find({"action": "login_2fa", "html_preview": {"$regex": code}}, {"_id": 1, "html_preview": 1}):
        await db.email_logs.update_one({"_id": log["_id"]}, {"$set": {"html_preview": log["html_preview"].replace(code, "••••••")}})


async def verify_2fa(challenge_id: str, code: str) -> str:
    ch = await db.login_2fa_challenges.find_one({"challenge_id": challenge_id}, {"_id": 0})
    if not ch or _now() > _parse(ch["expires_at"]):
        raise HTTPException(status_code=400, detail="El código expiró. Inicie sesión nuevamente.")
    if ch.get("attempts", 0) >= 5:
        await db.login_2fa_challenges.delete_one({"challenge_id": challenge_id})
        raise HTTPException(status_code=400, detail="Demasiados intentos. Inicie sesión nuevamente.")
    if _hash_code((code or "").strip()) != ch["code_hash"]:
        await db.login_2fa_challenges.update_one({"challenge_id": challenge_id}, {"$inc": {"attempts": 1}})
        raise HTTPException(status_code=400, detail="Código incorrecto.")
    await db.login_2fa_challenges.delete_one({"challenge_id": challenge_id})
    return ch["user_id"]


async def resend_2fa(challenge_id: str):
    ch = await db.login_2fa_challenges.find_one({"challenge_id": challenge_id}, {"_id": 0})
    if not ch:
        raise HTTPException(status_code=400, detail="La verificación expiró. Inicie sesión nuevamente.")
    policy = await get_policy()
    code = f"{secrets.randbelow(1_000_000):06d}"
    exp = _now() + timedelta(minutes=policy["otp_ttl_minutes"])
    await db.login_2fa_challenges.update_one({"challenge_id": challenge_id}, {"$set": {
        "code_hash": _hash_code(code), "attempts": 0, "expires_at": exp.isoformat(), "expires_at_dt": exp}})
    user = await db.users.find_one({"user_id": ch["user_id"]}, {"_id": 0})
    await send_2fa_email(user, code, policy["otp_ttl_minutes"])
