import os
import secrets
import hashlib
import logging
from datetime import datetime, timedelta, timezone
from html import escape
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request
from pymongo import ReturnDocument

from lib.db import db
from lib.mail import send_email
from lib.security import hash_password, new_id, utcnow
from models.schemas import EmailIn, ResetPasswordIn, VerifyEmailIn

router = APIRouter(tags=["account"])

VERIFY_TTL_SECONDS = 600
RESET_TTL_SECONDS = 1800
logger = logging.getLogger(__name__)


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


async def _limit(purpose: str, identity: str, limit: int, seconds: int) -> bool:
    now = datetime.now(timezone.utc)
    bucket = int(now.timestamp()) // seconds
    key = _digest(f"{purpose}:{identity}:{bucket}")
    result = await db.auth_rate_limits.find_one_and_update(
        {"_id": key},
        {"$inc": {"count": 1}, "$setOnInsert": {"expires_at": now + timedelta(seconds=seconds * 2)}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return result["count"] <= limit


def _code() -> str:
    return f"{secrets.randbelow(1000000):06d}"


def _expiry(seconds: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()


def _code_email_html(code: str) -> str:
    return (
        '<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
        '<h2 style="margin:0 0 12px;font-size:18px;color:#1D4ED8">Verify your email</h2>'
        '<p style="margin:0 0 16px;font-size:14px;color:#334155">Your Poonji Finance verification code is:</p>'
        f'<p style="margin:0;font-size:32px;font-weight:bold;letter-spacing:8px;color:#0E1B33;font-family:monospace">{escape(code)}</p>'
        '<p style="margin:20px 0 0;font-size:12px;color:#94A3B8">Valid for 10 minutes. If you did not create an account, '
        "you can ignore this email. Poonji Finance never asks for codes or card details over phone.</p>"
        "</td></tr></table>"
    )


def _reset_email_html(link: str) -> str:
    return (
        '<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif">'
        '<h2 style="margin:0 0 12px;font-size:18px;color:#1D4ED8">Reset your password</h2>'
        '<p style="margin:0 0 16px;font-size:14px;color:#334155">We received a request to reset the password for your '
        "Poonji Finance account. The link below is valid for 30 minutes.</p>"
        f'<p style="margin:0"><a href="{escape(link)}" style="color:#1D4ED8;font-weight:bold">Reset your password</a></p>'
        '<p style="margin:20px 0 0;font-size:12px;color:#94A3B8">If you did not request this, you can ignore this email — '
        "your password stays unchanged.</p>"
        "</td></tr></table>"
    )


async def issue_verification(email: str) -> None:
    code = _code()
    await db.email_tokens.update_many({"email": email, "purpose": "verify", "used": False}, {"$set": {"used": True}})
    await db.email_tokens.insert_one({
        "id": new_id(), "email": email, "purpose": "verify", "code": code,
        "used": False, "expires_at": _expiry(VERIFY_TTL_SECONDS), "created_at": utcnow(),
    })
    await send_email(to=email, subject="Your Poonji Finance verification code", html=_code_email_html(code))


@router.post("/auth/send-verification")
async def send_verification(body: EmailIn):
    email = body.email.lower()
    user = await db.users.find_one({"email": email})
    if user and not user.get("email_verified"):
        await issue_verification(email)
    return {"ok": True}


@router.post("/auth/verify-email")
async def verify_email(body: VerifyEmailIn):
    email = body.email.lower()
    tok = await db.email_tokens.find_one({"email": email, "purpose": "verify", "code": body.code.strip(), "used": False})
    if not tok or tok["expires_at"] < utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired code")
    await db.email_tokens.update_one({"id": tok["id"]}, {"$set": {"used": True}})
    await db.users.update_one({"email": email}, {"$set": {"email_verified": True}})
    return {"ok": True}


@router.post("/auth/forgot-password")
async def forgot_password(body: EmailIn, request: Request):
    email = body.email.strip().lower()
    client_ip = request.client.host if request.client else "unknown"
    if not await _limit("forgot-ip", client_ip, 12, 3600):
        raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")
    if not await _limit("forgot-email", email, 3, 3600):
        return {"ok": True}
    user = await db.users.find_one({"email": email})
    if user:
        frontend_url = os.environ.get("FRONTEND_URL", "").rstrip("/")
        if not frontend_url.startswith("https://"):
            logger.error("Password reset email not sent: FRONTEND_URL must be an HTTPS URL")
            return {"ok": True}
        token = secrets.token_urlsafe(32)
        await db.email_tokens.update_many({"email": email, "purpose": "reset", "used": False}, {"$set": {"used": True}})
        await db.email_tokens.insert_one({
            "id": new_id(), "email": email, "purpose": "reset", "token_hash": _digest(token),
            "used": False, "expires_at": _expiry(RESET_TTL_SECONDS), "created_at": utcnow(),
        })
        link = f"{frontend_url}/reset-password?token={quote(token)}"
        if not await send_email(to=email, subject="Reset your Poonji Finance password", html=_reset_email_html(link)):
            logger.error("Password reset email could not be delivered")
    return {"ok": True}


@router.post("/auth/reset-password")
async def reset_password(body: ResetPasswordIn):
    tok = await db.email_tokens.find_one_and_update(
        {"token_hash": _digest(body.token), "purpose": "reset", "used": False, "expires_at": {"$gt": utcnow()}},
        {"$set": {"used": True}},
        return_document=ReturnDocument.BEFORE,
    )
    if not tok:
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")
    await db.users.update_one({"email": tok["email"]}, {"$set": {"password_hash": hash_password(body.password)}, "$inc": {"session_version": 1}})
    await db.email_tokens.update_many({"email": tok["email"], "purpose": "reset"}, {"$set": {"used": True}})
    return {"ok": True}
