#!/usr/bin/env python3
"""NASA-004 independent, read-only, two-principal live transport acceptance.

Does NOT implement an endpoint, authenticate users, or certify a Studio by itself.
The runner sends only GET requests. Credentials are read from environment, and
neither credentials nor response bodies are retained in evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import os
from pathlib import Path
import re
import ssl
import sys
import time
from urllib.parse import urlsplit

from studio_acceptance import verify_wav, ContractFailure

MAX_BYTES = 50 * 1024 * 1024
TIMEOUT_SECONDS = 12
HEX64 = re.compile(r"^[0-9a-f]{64}$")
CASE_RULES = {
    "A_PROJECT_OWN": ("A", {200}, "json"),
    "B_PROJECT_OWN": ("B", {200}, "json"),
    "B_PROJECT_A": ("B", {404}, "deny"),
    "A_PROJECT_B": ("A", {404}, "deny"),
    "ANON_PROJECT_A": ("ANON", {401, 403}, "deny"),
    "A_AUDIO_R1": ("A", {200}, "wav_r1"),
    "A_AUDIO_R2": ("A", {200}, "wav_r2"),
    "B_AUDIO_A_R1": ("B", {404}, "deny"),
    "ANON_AUDIO_A_R1": ("ANON", {401, 403}, "deny"),
    "A_HISTORY_R1": ("A", {200}, "json"),
    "B_HISTORY_A": ("B", {404}, "deny"),
    "A_UNBOUND_ARTIFACT": ("A", {404}, "deny"),
}


def require(condition, message):
    if not condition:
        raise ContractFailure(message)


def _origin(base):
    parsed = urlsplit(base)
    require(parsed.scheme in ("http", "https") and parsed.hostname and not parsed.username and not parsed.password, "invalid base URL")
    require(not parsed.query and not parsed.fragment and parsed.path in ("", "/"), "base must be origin only")
    require(parsed.scheme == "https" or parsed.hostname in ("localhost", "127.0.0.1", "::1"), "nonlocal HTTP prohibited")
    return parsed


def _path(raw):
    require(isinstance(raw, str) and raw.startswith("/") and not raw.startswith("//"), "path must be relative to app origin")
    parsed = urlsplit(raw)
    require(not parsed.scheme and not parsed.netloc and not parsed.fragment, "cross-origin or fragment path prohibited")
    require(not re.search(r"(?:token|secret|cookie|capability|auth|key)=", parsed.query, re.I), "potential secret in query")
    require(not re.search(r"(?:^|/)\.\.(?:/|$)", parsed.path), "path traversal denied")
    return raw


def validate_fixture(fixture):
    origin = _origin(fixture.get("base_url", ""))
    require(HEX64.fullmatch(fixture.get("target_commit", "")), "exact target SHA required")
    wav = fixture.get("audio", {})
    require(isinstance(wav, dict) and set(wav) == {"r1", "r2"}, "exact two WAV identities required")
    for rev, item in wav.items():
        require(isinstance(item, dict) and HEX64.fullmatch(item.get("sha256", "")) and HEX64.fullmatch(item.get("revision_id", "")), f"{rev} expected exact WAV+revision SHA")
    require(wav["r1"]["revision_id"] != wav["r2"]["revision_id"], "R1/R2 revisions must be distinct")
    require(wav["r1"]["sha256"] != wav["r2"]["sha256"], "R1/R2 audio must be distinct")
    routes = fixture.get("routes")
    require(isinstance(routes, dict) and set(routes) == set(CASE_RULES), "all twelve fixed cases required; no custom success statuses")
    for cid, path in routes.items():
        _path(path)
    require(routes["A_AUDIO_R1"] == routes["B_AUDIO_A_R1"] == routes["ANON_AUDIO_A_R1"], "A/B/anonymous must request identical R1 URL")
    require(routes["A_PROJECT_OWN"] == routes["B_PROJECT_A"] == routes["ANON_PROJECT_A"], "A/B/anonymous must request identical project A URL")
    require(routes["B_PROJECT_OWN"] == routes["A_PROJECT_B"], "cross-principal project B URL mismatch")
    require(routes["A_HISTORY_R1"] == routes["B_HISTORY_A"], "history must target identical resource")
    return origin


def fetch_read_only(origin, path, cookie=None, timeout=TIMEOUT_SECONDS):
    port = origin.port or (443 if origin.scheme == "https" else 80)
    connection = (http.client.HTTPSConnection(origin.hostname, port, timeout=timeout, context=ssl.create_default_context()) if origin.scheme == "https"
                  else http.client.HTTPConnection(origin.hostname, port, timeout=timeout))
    headers = {"Accept": "application/json, audio/wav", "Cache-Control": "no-cache"}
    if cookie is not None:
        headers["Cookie"] = cookie
    try:
        connection.request("GET", _path(path), headers=headers)
        response = connection.getresponse()
        status = response.status
        response_headers = {k.lower(): v for k, v in response.getheaders()}
        length_header = response_headers.get("content-length")
        if length_header is not None:
            require(length_header.isdigit() and int(length_header) <= MAX_BYTES, "oversized content-length")
        buf = bytearray()
        while True:
            piece = response.read(min(65536, MAX_BYTES + 1 - len(buf)))
            if not piece: break
            buf.extend(piece)
            require(len(buf) <= MAX_BYTES, "response exceeds limit")
        return status, response_headers, bytes(buf)
    finally:
        connection.close()


def run(fixture, creds, requester=fetch_read_only):
    origin = validate_fixture(fixture)
    require(creds.get("A") and creds.get("B") and creds["A"] != creds["B"], "two independent authenticated session cookies required")
    results = []
    started = time.monotonic()
    for cid, (principal, allowed, kind) in CASE_RULES.items():
        path = fixture["routes"][cid]
        t0 = time.monotonic()
        try:
            status, headers, blob = requester(origin, path, creds.get(principal))
            require(status in allowed, f"{cid}: HTTP {status} is not an allowed result")
            require(status < 300 and status not in (301, 302, 303, 307, 308) if kind != "deny" else status >= 400,
                    f"{cid}: unexpected redirect or response")
            case = {"case": cid, "result": "PASS", "http_status": status, "body_sha256": hashlib.sha256(blob).hexdigest(), "response_bytes": len(blob)}
            if kind == "deny":
                require(len(blob) <= 4096, f"{cid}: oversized denial body")
                canary = fixture.get("nonsecret_denial_canary", "TENANT_A_SECRET_CANARY")
                require(canary.encode() not in blob, f"{cid}: protected canary leaked")
            elif kind == "json":
                require("json" in headers.get("content-type", "").lower(), f"{cid}: expected application JSON")
                body = json.loads(blob)
                require(isinstance(body, (dict, list)), f"{cid}: malformed JSON response")
            elif kind.startswith("wav_"):
                expected = fixture["audio"][kind[-2:]]
                require("audio/" in headers.get("content-type", "").lower(), f"{cid}: expected audio Content-Type")
                observed = verify_wav(blob)
                require(observed["sha256"] == expected["sha256"], f"{cid}: WAV bytes do not match expected SHA")
                # A digest proves bytes, not revision attachment. Require explicit
                # authenticated revision-binding evidence from real transport.
                require(headers.get("x-source-revision-id") == expected["revision_id"], f"{cid}: missing/mismatched authoritative revision binding")
                require(headers.get("x-audio-sha256") == expected["sha256"], f"{cid}: missing/mismatched audio identity header")
                case["pcm_sha256"] = observed["pcm_sha256"]
                case["frames"] = observed["frames"]
                case["sample_rate"] = observed["sample_rate"]
                case["channels"] = observed["channels"]
            case["elapsed_ms"] = int((time.monotonic() - t0) * 1000)
            results.append(case)
        except (ContractFailure, OSError, ValueError, http.client.HTTPException) as err:
            results.append({"case": cid, "result": "FAIL", "error": str(err)[:180]})
            break
    failure = next((x for x in results if x["result"] != "PASS"), None)
    return {"schema":"sara-manus.nasa004-live-readonly.v1",
            "verdict": "PASS" if not failure and len(results) == len(CASE_RULES) else "HOLD",
            "evidence_kind":"EXECUTED_HTTP_READ_ONLY", "target_commit":fixture["target_commit"],
            "target_origin": origin.scheme + "://" + origin.netloc,
            "checked_cases":len(results),"required_cases":len(CASE_RULES),
            "elapsed_ms":int((time.monotonic()-started)*1000),
            "first_failed_boundary":failure["case"] if failure else None,
            "cases":results,
            "limits":"Neither UI/cinema race handling, deployment, nor creative/audio quality certified. Operator-supplied expected SHA/revision IDs require canonical provenance."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cookie-a-env", default="NASA004_COOKIE_A")
    parser.add_argument("--cookie-b-env", default="NASA004_COOKIE_B")
    args = parser.parse_args()
    # NEVER serialize or print auth cookies, even on failures.
    try:
        fixture = json.loads(args.fixture.read_text())
        receipt = run(fixture, {"A":os.getenv(args.cookie_a_env),"B":os.getenv(args.cookie_b_env)})
    except (ContractFailure, ValueError, KeyError, OSError) as exc:
        receipt = {"schema":"sara-manus.nasa004-live-readonly.v1","verdict":"HOLD","first_failed_boundary":str(exc)[:200],"checked_cases":0}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    print(f"NASA004 LIVE READ-ONLY: {receipt['verdict']} ({receipt.get('checked_cases',0)}/{len(CASE_RULES)})")
    if receipt.get("first_failed_boundary"):
        print("FIRST FAILED: " + receipt["first_failed_boundary"])
    return 0 if receipt["verdict"] == "PASS" else 2


if __name__ == "__main__":
    sys.exit(main())
