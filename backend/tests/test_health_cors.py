import asyncio
from types import SimpleNamespace

from fastapi import HTTPException
from fastapi.testclient import TestClient

import server


def test_health_reports_database_state(monkeypatch):
    class Admin:
        async def command(self, name):
            assert name == "ping"
            return {"ok": 1}

    monkeypatch.setattr(server, "client", SimpleNamespace(admin=Admin()))
    assert asyncio.run(server.health()) == {"status": "ok", "database": "connected"}

    class FailedAdmin:
        async def command(self, name):
            raise OSError("database offline")

    monkeypatch.setattr(server, "client", SimpleNamespace(admin=FailedAdmin()))
    try:
        asyncio.run(server.health())
        assert False, "health must fail when MongoDB is offline"
    except HTTPException as error:
        assert error.status_code == 503


def test_cors_preflight_allows_site_with_credentials():
    response = TestClient(server.app).options(
        "/api/auth/login",
        headers={"Origin": "https://poonjifinance.com", "Access-Control-Request-Method": "POST"},
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://poonjifinance.com"
    assert response.headers["access-control-allow-credentials"] == "true"
