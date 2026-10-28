"""Concurrent API load test (no LLM calls unless a worker is running).

Creates N users, then fires N simultaneous POST /storyboards/generate plus
N GET /storyboards/jobs and N GET /storyboards/{id}, and reports status codes
and latency. Target: zero HTTP 500s.

    python scripts/load_test_api.py --base http://127.0.0.1:8011 --n 20
"""
import argparse
import concurrent.futures as cf
import json
import statistics
import time
import uuid

import httpx

PAYLOAD = {"idea": "A 30 second espresso routine for busy mornings", "goal": "educate", "tone": "calm",
           "style": "talking_head", "audience": "Coffee lovers", "duration": 30, "platform": "reels"}


def make_user(base: str) -> dict:
    email = f"load_{uuid.uuid4().hex[:10]}@example.com"
    pw = "load-test-password"  # gitleaks:allow (throwaway test account)
    httpx.post(f"{base}/auth/register", json={"username": email.split("@")[0], "email": email, "password": pw}, timeout=30)
    r = httpx.post(f"{base}/auth/login", json={"email": email, "password": pw}, timeout=30)
    # Since Phase F the session token comes back as a cookie, not in the body.
    token = r.cookies.get("grovii_session") or r.cookies.get("__Host-grovii_session")
    return {"Authorization": f"Bearer {token}"}


def timed(method: str, url: str, headers: dict, **kw):
    start = time.perf_counter()
    try:
        r = httpx.request(method, url, headers=headers, timeout=60, **kw)
        return r.status_code, (time.perf_counter() - start) * 1000, r
    except Exception as e:  # noqa: BLE001
        return f"error:{type(e).__name__}", (time.perf_counter() - start) * 1000, None


def pct(values, p):
    values = sorted(values)
    return values[min(len(values) - 1, int(round(p / 100 * (len(values) - 1))))] if values else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:8011")
    ap.add_argument("--n", type=int, default=20)
    args = ap.parse_args()

    users = [make_user(args.base) for _ in range(args.n)]
    report = {}

    with cf.ThreadPoolExecutor(max_workers=args.n * 3) as pool:
        gen = list(pool.map(lambda h: timed("POST", f"{args.base}/storyboards/generate", h, json=PAYLOAD), users))
        # Pair each user with THEIR OWN storyboard (refused generates have none).
        own = [(h, r.json()["storyboard_id"]) for h, (code, _, r) in zip(users, gen) if code == 200]
        reads = [pool.submit(timed, "GET", f"{args.base}/storyboards/jobs", h) for h in users]
        reads += [pool.submit(timed, "GET", f"{args.base}/storyboards/{sid}", h) for h, sid in own]
        reads = [f.result() for f in reads]

    for name, results in (("POST /storyboards/generate", gen), ("GET jobs + storyboard (concurrent)", reads)):
        codes: dict = {}
        for code, _, _ in results:
            codes[str(code)] = codes.get(str(code), 0) + 1
        lat = [ms for _, ms, _ in results]
        report[name] = {"requests": len(results), "status_codes": codes,
                        "p50_ms": round(statistics.median(lat), 1), "p95_ms": round(pct(lat, 95), 1),
                        "max_ms": round(max(lat), 1)}
    print(json.dumps(report, indent=2))
    total_500 = sum(v["status_codes"].get("500", 0) for v in report.values())
    print(f"HTTP 500 count: {total_500}")


if __name__ == "__main__":
    main()
