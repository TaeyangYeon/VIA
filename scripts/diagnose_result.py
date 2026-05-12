"""
Runtime diagnostic: queries the LIVE backend and prints exactly what the frontend receives.

Usage:
  1. Start backend: python -m uvicorn backend.main:app --port 8000
  2. Run an execution through the UI (wait for "success" status)
  3. Run: python scripts/diagnose_result.py
     OR: python scripts/diagnose_result.py <execution_id>
"""
from __future__ import annotations

import json
import sys

import httpx

BASE = "http://localhost:8000"


def main() -> None:
    client = httpx.Client(timeout=10)

    # ── Step 1: Resolve execution_id ─────────────────────────────────────────
    if len(sys.argv) > 1:
        eid = sys.argv[1]
        print(f"Using provided execution_id: {eid}")
    else:
        try:
            resp = client.get(f"{BASE}/api/execute/history")
        except httpx.ConnectError:
            print("ERROR: Cannot connect to backend at http://localhost:8000")
            print("       Start the server first: python -m uvicorn backend.main:app --port 8000")
            return

        if resp.status_code != 200:
            print(f"ERROR: GET /api/execute/history → HTTP {resp.status_code}")
            print(resp.text[:500])
            return

        history = resp.json()
        if isinstance(history, dict):
            execs = history.get("executions", [])
        elif isinstance(history, list):
            execs = history
        else:
            print(f"Unexpected history format: {type(history).__name__}")
            print(json.dumps(history, indent=2, ensure_ascii=False)[:500])
            return

        if not execs:
            print("No executions found. Run an execution through the UI first.")
            return

        latest = execs[0]
        eid = latest["execution_id"] if isinstance(latest, dict) else str(latest)
        status = latest.get("status", "?") if isinstance(latest, dict) else "?"
        print(f"Using latest execution: {eid}  (status={status})")

    # ── Step 2: GET execution status ─────────────────────────────────────────
    try:
        resp = client.get(f"{BASE}/api/execute/{eid}")
    except httpx.ConnectError:
        print("ERROR: Cannot connect to backend.")
        return

    print(f"\n{'='*60}")
    print(f"GET /api/execute/{eid}")
    print(f"HTTP {resp.status_code}")
    print(f"{'='*60}")

    if resp.status_code != 200:
        print(f"ERROR body: {resp.text[:500]}")
        return

    # ── Step 3: Check raw JSON ────────────────────────────────────────────────
    try:
        body = resp.json()
    except Exception as e:
        print(f"\n*** CRITICAL: Response is not valid JSON: {e} ***")
        print(f"Raw body (first 500 chars):\n{resp.text[:500]}")
        return

    print(f"\n[Response Keys]  {list(body.keys())}")
    print(f"  status        : {body.get('status')!r}")
    print(f"  error         : {body.get('error')!r}")
    print(f"  'result' key present : {'result' in body}")
    print(f"  result is None       : {body.get('result') is None}")
    print(f"  result type          : {type(body.get('result')).__name__}")

    result = body.get("result")

    # ── Step 4: Diagnose result field ─────────────────────────────────────────
    print(f"\n[Frontend condition check]")
    status_ok = body.get("status") == "success"
    result_truthy = bool(result)
    print(f"  res.status === 'success' : {status_ok}")
    print(f"  res.result is truthy     : {result_truthy}")
    print(f"  setResult would fire     : {status_ok and result_truthy}")

    if result is None:
        print(f"\n{'!'*60}")
        print("BUG FOUND: result is null in the API response.")
        print("The backend did not populate state.result after execution.")
        print(f"{'!'*60}")
        print(f"\nFull response:\n{json.dumps(body, indent=2, ensure_ascii=False)}")
        return

    if not isinstance(result, dict):
        print(f"\n{'!'*60}")
        print(f"BUG FOUND: result is {type(result).__name__}, expected dict.")
        print(f"Value: {str(result)[:200]}")
        print(f"{'!'*60}")
        return

    # ── Step 5: Inspect result fields ─────────────────────────────────────────
    EXPECTED_KEYS = [
        "summary", "algorithm_code", "algorithm_explanation",
        "pipeline", "inspection_plan", "metrics",
        "item_results", "improvement_suggestions",
        "decision", "decision_reason",
    ]

    print(f"\n[Result keys present]  {list(result.keys())}")
    missing = [k for k in EXPECTED_KEYS if k not in result]
    if missing:
        print(f"\n*** MISSING KEYS: {missing} ***")

    print(f"\n[Result field values]")
    for key in EXPECTED_KEYS:
        val = result.get(key)
        if val is None:
            tag = "  [NULL]"
            print(f"  {key:<30}: None  {tag}")
        elif isinstance(val, str):
            print(f"  {key:<30}: {repr(val[:80])}")
        elif isinstance(val, list):
            print(f"  {key:<30}: list[{len(val)}]")
        elif isinstance(val, dict):
            dk = list(val.keys())[:5]
            print(f"  {key:<30}: dict{{{', '.join(dk)}}}")
        else:
            print(f"  {key:<30}: {type(val).__name__} = {str(val)[:80]}")

    # ── Step 6: Frontend empty-state condition ────────────────────────────────
    summary = result.get("summary")
    print(f"\n[ResultPanel empty-state check]")
    print(f"  result.summary value  : {repr(summary)}")
    print(f"  !result.summary       : {not summary}")
    if not summary:
        print(f"\n{'!'*60}")
        print("BUG FOUND: result.summary is falsy — ResultPanel will show empty state.")
        print(f"  summary={summary!r}  (null/empty/undefined maps to null in Redux)")
        print(f"{'!'*60}")
    else:
        print(f"\n  ResultPanel SHOULD show content (summary is non-empty).")
        print(f"  If it still shows empty, the bug is in the frontend Redux dispatch.")
        print(f"  → Check the 'Debug Result' button output in the browser.")

    # ── Step 7: JSON-serializability check ───────────────────────────────────
    print(f"\n[JSON round-trip check]")
    try:
        serialized = json.dumps(result, ensure_ascii=False)
        reparsed = json.loads(serialized)
        if reparsed.get("summary") == summary:
            print(f"  JSON serialization: OK  (summary survives round-trip)")
        else:
            print(f"  *** summary changed after JSON round-trip! ***")
            print(f"      before: {summary!r}")
            print(f"      after : {reparsed.get('summary')!r}")
    except Exception as e:
        print(f"\n{'!'*60}")
        print(f"BUG FOUND: result contains non-JSON-serializable value: {e}")
        print(f"{'!'*60}")

    # ── Step 8: Full response dump ────────────────────────────────────────────
    print(f"\n[Full response body (truncated at 4000 chars)]")
    print(json.dumps(body, indent=2, ensure_ascii=False)[:4000])


if __name__ == "__main__":
    main()
