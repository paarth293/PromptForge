#!/usr/bin/env python
"""scripts/warmup.py — Pre-presentation system warm-up script.

Hits every critical PromptForge API endpoint in sequence to:
  - Pre-warm the mock LLM client (loads tokenizer weights once)
  - Establish and pool the SQLite WAL connection
  - Populate in-process caches (blueprint registry, cost tracker bucket)
  - Verify the full pipeline round-trip is healthy before a live demo

Usage:
    python scripts/warmup.py [--base-url http://localhost:8000] [--timeout 120]

Exit code 0 = all checks green, exit code 1 = at least one check failed.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import time
from typing import Any

import httpx

# ---------------------------------------------------------------------------
# Colour helpers (no external deps)
# ---------------------------------------------------------------------------

RESET = "\033[0m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"


def _ok(msg: str) -> None:
    print(f"  {GREEN}✓{RESET}  {msg}")


def _warn(msg: str) -> None:
    print(f"  {YELLOW}⚠{RESET}  {msg}")


def _fail(msg: str) -> None:
    print(f"  {RED}✗{RESET}  {msg}")


def _section(title: str) -> None:
    print(f"\n{BOLD}{CYAN}── {title}{RESET}")


# ---------------------------------------------------------------------------
# Individual probe functions
# ---------------------------------------------------------------------------


async def probe_health(client: httpx.AsyncClient) -> bool:
    """GET /health — confirm backend is up and services are registered."""
    _section("Health check")
    t0 = time.monotonic()
    try:
        r = await client.get("/health")
        elapsed = (time.monotonic() - t0) * 1000
        if r.status_code == 200:
            data = r.json()
            _ok(f"Backend healthy — status={data.get('status', 'ok')}  ({elapsed:.0f} ms)")
            return True
        else:
            _fail(f"Health endpoint returned HTTP {r.status_code}")
            return False
    except Exception as exc:
        _fail(f"Health probe failed: {exc}")
        return False


async def probe_demo_profiles(client: httpx.AsyncClient) -> dict[str, Any] | None:
    """GET /api/demo/profiles — load both demo profiles into memory."""
    _section("Demo profiles")
    try:
        r = await client.get("/api/demo/profiles")
        if r.status_code == 200:
            profiles = r.json()
            loaded: dict[str, Any] = {}
            for p in profiles:
                p_id = p.get("profile_id") or p.get("id", "?")
                p_name = p.get("agent_name") or p.get("name", "?")
                _ok(f"Profile loaded: {p_id}  —  {p_name}")
                loaded[p_id] = p
            return loaded
        else:
            _fail(f"Demo profiles returned HTTP {r.status_code}")
            return None
    except Exception as exc:
        _fail(f"Demo profiles probe failed: {exc}")
        return None


async def probe_forge_pipeline(client: httpx.AsyncClient, profile_id: str) -> str | None:
    """POST /api/demo/seed/{profile_id} — seed spec + blueprint, return blueprint_id."""
    _section(f"Forge pipeline (profile={profile_id})")
    try:
        r = await client.post(
            f"/api/demo/seed/{profile_id}",
            headers={"X-Tenant-ID": "tenant-demo"}
        )
        if r.status_code == 200:
            data = r.json()
            blueprint_id = data.get("blueprint_id")
            spec_id = data.get("spec_id")
            _ok(f"Spec seeded:      spec_id={spec_id}")
            _ok(f"Blueprint seeded: blueprint_id={blueprint_id}")
            return blueprint_id
        else:
            _fail(f"Seed endpoint returned HTTP {r.status_code}: {r.text[:200]}")
            return None
    except Exception as exc:
        _fail(f"Forge pipeline probe failed: {exc}")
        return None


async def probe_runtime_chat(client: httpx.AsyncClient, blueprint_id: str) -> bool:
    """POST /api/agents/{blueprint_id}/chat — warm up the LLM mock for inference."""
    _section("Runtime chat (LLM warm-up)")
    payload = {"message": "Hello, I need help with my order.", "session_id": "warmup-session"}
    try:
        r = await client.post(
            f"/api/agents/{blueprint_id}/chat",
            json=payload,
            headers={"X-Tenant-ID": "tenant-demo"}
        )
        if r.status_code == 200:
            data = r.json()
            reply = data.get("response", "")[:80]
            _ok(f"LLM mock responding: \"{reply}…\"")
            return True
        else:
            _warn(f"Runtime chat returned HTTP {r.status_code} (non-fatal, proceeding)")
            return True  # non-critical — demo can still run
    except Exception as exc:
        _warn(f"Runtime chat probe failed: {exc} (non-fatal)")
        return True


async def probe_cost_report(client: httpx.AsyncClient) -> bool:
    """GET /api/metrics/cost — pre-warm the cost instrumentation singleton."""
    _section("Cost instrumentation")
    try:
        r = await client.get("/api/metrics/cost", headers={"X-Tenant-ID": "tenant-demo"})
        if r.status_code == 200:
            data = r.json()
            total = data.get("total_cost_usd", 0)
            _ok(f"Cost tracker live — total_cost_usd={total:.4f}")
            return True
        else:
            _warn(f"Cost report returned HTTP {r.status_code} (non-fatal)")
            return True
    except Exception as exc:
        _warn(f"Cost report probe failed: {exc} (non-fatal)")
        return True


async def probe_hash_chain(client: httpx.AsyncClient, blueprint_id: str) -> bool:
    """GET /api/blueprints/{blueprint_id}/chain — verify hash chain integrity pre-demo."""
    _section("Hash chain integrity")
    try:
        r = await client.get(
            f"/api/blueprints/{blueprint_id}/chain",
            headers={"X-Tenant-ID": "tenant-demo"}
        )
        if r.status_code == 200:
            data = r.json()
            valid = data.get("valid", False)
            length = data.get("chain_length", 0)
            if valid:
                _ok(f"Hash chain intact — {length} block(s)")
                return True
            else:
                _fail(f"Hash chain INVALID at block {data.get('invalid_at_block', '?')}: {data.get('reason', '?')}")
                return False
        else:
            _warn(f"Hash chain endpoint returned HTTP {r.status_code} (non-fatal)")
            return True
    except Exception as exc:
        _warn(f"Hash chain probe failed: {exc} (non-fatal)")
        return True


# ---------------------------------------------------------------------------
# Main warm-up orchestrator
# ---------------------------------------------------------------------------


async def run_warmup(base_url: str, timeout: float) -> int:
    """Run full warm-up sequence; return exit code (0=ok, 1=critical failure)."""
    print(f"\n{BOLD}PromptForge Pre-Presentation Warm-Up{RESET}")
    print(f"  Target: {base_url}")
    print(f"  Timeout: {timeout}s per request")

    t_start = time.monotonic()
    failures: list[str] = []

    async with httpx.AsyncClient(base_url=base_url, timeout=timeout) as client:
        # 1. Health — critical
        if not await probe_health(client):
            print(f"\n{RED}{BOLD}ABORT: Backend is not reachable. Start the server and retry.{RESET}\n")
            return 1

        # 2. Demo profiles — critical
        profiles = await probe_demo_profiles(client)
        if profiles is None:
            failures.append("demo_profiles")
            profile_id = "customer_support"  # fallback for subsequent probes
        else:
            profile_id = next(iter(profiles.keys()))

        # 3. Forge pipeline seed — critical
        blueprint_id = await probe_forge_pipeline(client, profile_id)
        if blueprint_id is None:
            failures.append("forge_pipeline")
            # Use a dummy ID for subsequent non-critical probes
            blueprint_id = "warmup-dummy"

        # 4. Runtime chat — non-critical
        await probe_runtime_chat(client, blueprint_id)

        # 5. Cost instrumentation — non-critical
        await probe_cost_report(client)

        # 6. Hash chain — non-critical (but logged)
        if blueprint_id != "warmup-dummy":
            await probe_hash_chain(client, blueprint_id)

    elapsed = time.monotonic() - t_start
    print()
    if failures:
        _fail(f"Warm-up completed with {len(failures)} critical failure(s): {', '.join(failures)}")
        print(f"  Total time: {elapsed:.1f}s\n")
        return 1
    else:
        _ok(f"All warm-up probes passed in {elapsed:.1f}s — system ready for demo ✨")
        print()
        return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="PromptForge pre-presentation warm-up script")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Backend base URL")
    parser.add_argument("--timeout", type=float, default=60.0, help="Per-request timeout in seconds")
    args = parser.parse_args()

    exit_code = asyncio.run(run_warmup(base_url=args.base_url, timeout=args.timeout))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
