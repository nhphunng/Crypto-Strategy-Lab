from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import httpx
import pytest

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(
        os.getenv("CSL_RUN_GENERATED_E2E") != "1",
        reason="set CSL_RUN_GENERATED_E2E=1 for the generated-strategy Compose E2E",
    ),
]

ROOT = Path(__file__).parents[3]
COMPOSE = [
    "docker",
    "compose",
    "-f",
    str(ROOT / "docker-compose.yml"),
    "-f",
    str(ROOT / "docker-compose.generated.yml"),
    "-f",
    str(ROOT / "docker-compose.e2e.yml"),
]


def test_user_stories_5_to_7_generate_activate_restart_and_reuse() -> None:
    base_url = os.getenv("CSL_GENERATED_E2E_BASE_URL", "http://127.0.0.1:8000")
    with httpx.Client(base_url=base_url, timeout=15) as client:
        generated = _generate(
            client,
            {"sourceType": "STRATEGY_NAME", "strategyName": "Donchian breakout"},
        )
        assert len(generated["drafts"]) == 1
        draft = _draft(client, generated["drafts"][0]["id"])
        assert draft["status"] == "READY_FOR_CONFIRMATION"
        assert draft["validationReport"]["status"] == "PASSED"
        assert draft["evidence"] and draft["assumptions"]

        activated = client.post(
            f"/api/v1/strategy-generation-drafts/{draft['id']}/activate",
            json={
                "draftFingerprint": draft["draftFingerprint"],
                "artifactFingerprint": draft["validationReport"]["artifactFingerprint"],
                "validationReportId": draft["validationReport"]["id"],
                "confirmed": True,
            },
        )
        activated.raise_for_status()
        identity = activated.json()["data"]
        _assert_catalog_contains(client, identity["strategyId"], identity["strategyVersion"])

        extracted = _generate(
            client,
            {
                "sourceType": "NATURAL_LANGUAGE",
                "content": "MULTI_STRATEGY_FIXTURE: extract breakout and reversion independently.",
            },
        )
        assert len(extracted["drafts"]) == 2
        extracted_drafts = [_draft(client, item["id"]) for item in extracted["drafts"]]
        assert {item["status"] for item in extracted_drafts} == {"READY_FOR_CONFIRMATION"}
        assert len({item["id"] for item in extracted_drafts}) == 2

    subprocess.run([*COMPOSE, "restart", "api"], cwd=ROOT, check=True, timeout=60)
    with httpx.Client(base_url=base_url, timeout=10) as restarted:
        _wait_ready(restarted)
        _assert_catalog_contains(restarted, identity["strategyId"], identity["strategyVersion"])


def _generate(client: httpx.Client, payload: dict[str, object]) -> dict[str, object]:
    response = client.post("/api/v1/strategy-generation-requests", json=payload)
    response.raise_for_status()
    request = response.json()["data"]
    for _ in range(90):
        response = client.get(f"/api/v1/strategy-generation-requests/{request['id']}")
        response.raise_for_status()
        request = response.json()["data"]
        if request["status"] in {"COMPLETED", "FAILED"}:
            break
        time.sleep(1)
    assert request["status"] == "COMPLETED", request
    return request


def _draft(client: httpx.Client, identity: str) -> dict[str, object]:
    response = client.get(f"/api/v1/strategy-generation-drafts/{identity}")
    response.raise_for_status()
    return response.json()["data"]


def _assert_catalog_contains(client: httpx.Client, strategy_id: str, version: str) -> None:
    response = client.get("/api/v1/strategies")
    response.raise_for_status()
    entries = response.json()["data"]["strategies"]
    assert any(
        item["strategyId"] == strategy_id
        and item["strategyVersion"] == version
        and item["origin"] == "LLM_GENERATED"
        for item in entries
    )


def _wait_ready(client: httpx.Client) -> None:
    for _ in range(60):
        try:
            if client.get("/health/ready").status_code == 200:
                return
        except httpx.HTTPError:
            pass
        time.sleep(1)
    raise AssertionError("API did not become ready after restart")
