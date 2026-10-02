import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt
import pytest

from lib import security
from models.schemas import ResetPasswordIn
from routers import account


def test_password_reset_token_is_hashed_single_use_and_revokes_sessions(monkeypatch):
    raw = "test-reset-token-with-enough-entropy"
    stored = {"email": "user@example.com", "token_hash": account._digest(raw),
              "purpose": "reset", "used": False,
              "expires_at": (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()}
    user = {"password_hash": security.hash_password("old-password"), "session_version": 0}

    class Tokens:
        async def find_one_and_update(self, query, update, return_document):
            if stored["used"] or query["token_hash"] != stored["token_hash"]:
                return None
            before = stored.copy()
            stored.update(update["$set"])
            return before

        async def update_many(self, query, update):
            stored.update(update["$set"])

    class Users:
        async def update_one(self, query, update):
            user.update(update["$set"])
            user["session_version"] += update["$inc"]["session_version"]

    monkeypatch.setattr(account, "db", SimpleNamespace(email_tokens=Tokens(), users=Users()))
    old_session = security.create_token("user-id", "user@example.com", "customer", 0)

    asyncio.run(account.reset_password(ResetPasswordIn(token=raw, password="new-password")))
    assert raw != stored["token_hash"]
    assert stored["used"] is True
    assert security.verify_password("new-password", user["password_hash"])
    assert jwt.decode(old_session, security.JWT_SECRET, algorithms=["HS256"])["session_version"] != user["session_version"]
    with pytest.raises(Exception) as error:
        asyncio.run(account.reset_password(ResetPasswordIn(token=raw, password="another-password")))
    assert error.value.status_code == 400
