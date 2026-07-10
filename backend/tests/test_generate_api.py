"""Tests for the /api/generate SSE endpoint (regression for missing DB id).

Previously the route was persisted in a `finally` block *after* the final SSE
event had already been sent, so the injected id never reached the client. These
tests pin the fix: the id/share_id are injected into the route dict and the final
SSE event carries them.
"""

import json

import pytest

import app.routers.generate as gen
from app.routers.generate import _save_route_to_db
from app.models.route import Route


def test_save_route_to_db_injects_identifiers(db_session):
    """_save_route_to_db must mutate the route dict with id + share_id and persist a row."""
    route_data = {
        "title": "测试路线",
        "departure": "北京",
        "destination": "沈阳",
        "day_plans": [],
    }
    route_id = _save_route_to_db(db_session, route_data)

    # Identifiers injected into the dict (this is what the SSE final event forwards).
    assert route_data["id"] == route_id
    assert route_data["share_id"]

    # Row actually persisted.
    row = db_session.query(Route).filter(Route.id == route_id).first()
    assert row is not None
    assert row.share_id == route_data["share_id"]


def test_generate_final_event_carries_db_id(client, monkeypatch):
    """The final SSE event returned to the client must include the DB id/share_id."""

    async def fake_stream(**kwargs):
        yield 'data: {"stage": "geocode", "status": "done", "message": "x", "progress": 10}\n\n'
        yield (
            'data: {"route": {"title": "T", "departure": "北京", '
            '"destination": "沈阳", "day_plans": []}, "error": ""}\n\n'
        )

    def fake_save(db, route_data):
        route_data["id"] = "test-id-123"
        route_data["share_id"] = "shareabc"
        return "test-id-123"

    monkeypatch.setattr(gen, "generate_route_stream", fake_stream)
    monkeypatch.setattr(gen, "_save_route_to_db", fake_save)

    resp = client.post(
        "/api/generate",
        json={"departure": "北京", "destination": "沈阳", "days": 2},
    )
    assert resp.status_code == 200

    final = None
    for block in resp.text.split("\n\n"):
        block = block.strip()
        if block.startswith("data:") and '"route"' in block:
            payload = json.loads(block[len("data:"):].strip())
            if payload.get("route"):
                final = payload["route"]

    assert final is not None, "no final route event found in stream"
    assert final["id"] == "test-id-123"
    assert final["share_id"] == "shareabc"
