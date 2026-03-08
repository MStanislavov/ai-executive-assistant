"""Tests for the Run API endpoints."""

import asyncio

import pytest


@pytest.mark.asyncio
async def test_create_run(client):
    # First create a profile
    profile_resp = await client.post("/api/profiles", json={"name": "TestProfile"})
    profile_id = profile_resp.json()["id"]

    resp = await client.post(
        f"/api/profiles/{profile_id}/runs",
        json={"mode": "daily"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["mode"] == "daily"
    assert data["status"] == "pending"
    assert data["profile_id"] == profile_id
    assert "id" in data

    # Allow background task to be created (but it will fail since no real DB for background)
    await asyncio.sleep(0.1)


@pytest.mark.asyncio
async def test_create_run_profile_not_found(client):
    resp = await client.post(
        "/api/profiles/nonexistent/runs",
        json={"mode": "daily"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_run_invalid_mode(client):
    profile_resp = await client.post("/api/profiles", json={"name": "TestProfile"})
    profile_id = profile_resp.json()["id"]

    resp = await client.post(
        f"/api/profiles/{profile_id}/runs",
        json={"mode": "invalid_mode"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_runs(client):
    profile_resp = await client.post("/api/profiles", json={"name": "TestProfile"})
    profile_id = profile_resp.json()["id"]

    await client.post(f"/api/profiles/{profile_id}/runs", json={"mode": "daily"})
    await client.post(f"/api/profiles/{profile_id}/runs", json={"mode": "daily"})

    resp = await client.get(f"/api/profiles/{profile_id}/runs")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2

    await asyncio.sleep(0.1)


@pytest.mark.asyncio
async def test_get_run(client):
    profile_resp = await client.post("/api/profiles", json={"name": "TestProfile"})
    profile_id = profile_resp.json()["id"]

    run_resp = await client.post(
        f"/api/profiles/{profile_id}/runs", json={"mode": "daily"}
    )
    run_id = run_resp.json()["id"]

    resp = await client.get(f"/api/profiles/{profile_id}/runs/{run_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == run_id

    await asyncio.sleep(0.1)


@pytest.mark.asyncio
async def test_get_run_not_found(client):
    profile_resp = await client.post("/api/profiles", json={"name": "TestProfile"})
    profile_id = profile_resp.json()["id"]

    resp = await client.get(f"/api/profiles/{profile_id}/runs/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_run_wrong_profile(client):
    p1 = await client.post("/api/profiles", json={"name": "Profile1"})
    p2 = await client.post("/api/profiles", json={"name": "Profile2"})
    p1_id = p1.json()["id"]
    p2_id = p2.json()["id"]

    run_resp = await client.post(f"/api/profiles/{p1_id}/runs", json={"mode": "daily"})
    run_id = run_resp.json()["id"]

    # Try to access run via wrong profile
    resp = await client.get(f"/api/profiles/{p2_id}/runs/{run_id}")
    assert resp.status_code == 404

    await asyncio.sleep(0.1)
