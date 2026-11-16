#!/usr/bin/env python3
"""Send one frozen chat-completions fixture and preserve its raw SSE evidence."""

from __future__ import annotations

import argparse
import hashlib
import http.client
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("fixture", type=Path, help="frozen JSON request body")
    parser.add_argument("--url", default="http://127.0.0.1:8000/v1/chat/completions")
    parser.add_argument("--trial-id", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=1800.0)
    args = parser.parse_args()

    body = args.fixture.read_bytes()
    # Fail before sending if the fixture is malformed.
    json.loads(body)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    request_copy = args.output_dir / "request_sent.json"
    request_copy.write_bytes(body)
    raw_path = args.output_dir / "response.sse"
    events_path = args.output_dir / "events.jsonl"
    summary_path = args.output_dir / "summary.json"

    url = urlsplit(args.url)
    if url.scheme != "http":
        raise SystemExit("Only loopback HTTP is supported by this runner")
    path = url.path or "/"
    if url.query:
        path += "?" + url.query
    conn = http.client.HTTPConnection(url.hostname, url.port or 80, timeout=args.timeout)
    start_utc = utc_now()
    start = time.monotonic()
    first_byte_seconds = None
    status = None
    headers: dict[str, str] = {}
    event_data: list[str] = []
    events: list[dict] = []
    usage_objects: list[dict] = []
    timing_objects: list[dict] = []
    finish_reasons: list[str] = []
    output_text: list[str] = []
    tool_call_deltas: list[dict] = []
    tool_calls_by_index: dict[int, dict] = {}
    error: str | None = None

    def flush_event() -> bool:
        nonlocal event_data
        if not event_data:
            return False
        payload = "\n".join(event_data)
        event_data = []
        if payload.strip() == "[DONE]":
            return True
        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            events.append({"unparsed_data": payload})
            return False
        events.append(event)
        if isinstance(event.get("usage"), dict):
            usage_objects.append(event["usage"])
        if isinstance(event.get("timings"), dict):
            timing_objects.append(event["timings"])
        for choice in event.get("choices", []) or []:
            if choice.get("finish_reason") is not None:
                finish_reasons.append(choice["finish_reason"])
            delta = choice.get("delta") or {}
            if isinstance(delta.get("content"), str):
                output_text.append(delta["content"])
            if delta.get("tool_calls"):
                tool_call_deltas.extend(delta["tool_calls"])
                for fragment in delta["tool_calls"]:
                    index = int(fragment.get("index", 0))
                    call = tool_calls_by_index.setdefault(
                        index,
                        {"index": index, "id": None, "type": None, "function": {"name": "", "arguments": ""}},
                    )
                    if fragment.get("id") is not None:
                        call["id"] = fragment["id"]
                    if fragment.get("type") is not None:
                        call["type"] = fragment["type"]
                    function = fragment.get("function") or {}
                    call["function"]["name"] += function.get("name") or ""
                    call["function"]["arguments"] += function.get("arguments") or ""
        return False

    try:
        conn.request(
            "POST",
            path,
            body=body,
            headers={"Content-Type": "application/json", "Accept": "text/event-stream"},
        )
        response = conn.getresponse()
        status = response.status
        headers = {k.lower(): v for k, v in response.getheaders()}
        with raw_path.open("wb") as raw:
            with events_path.open("w", encoding="utf-8") as event_file:
                while True:
                    line = response.readline()
                    if not line:
                        break
                    if first_byte_seconds is None:
                        first_byte_seconds = time.monotonic() - start
                    raw.write(line)
                    if line in (b"\n", b"\r\n"):
                        if flush_event():
                            break
                        if events:
                            event_file.write(json.dumps(events[-1], ensure_ascii=False) + "\n")
                    elif line.startswith(b"data:"):
                        event_data.append(line[5:].decode("utf-8", errors="replace").lstrip())
                if flush_event():
                    if events:
                        event_file.write(json.dumps(events[-1], ensure_ascii=False) + "\n")
    except Exception as exc:  # Preserve connection and server failures as evidence.
        error = f"{type(exc).__name__}: {exc}"
        if not raw_path.exists():
            raw_path.write_bytes(b"")
        if not events_path.exists():
            events_path.write_text("", encoding="utf-8")
    finally:
        conn.close()

    end = time.monotonic()
    summary = {
        "trial_id": args.trial_id,
        "fixture": str(args.fixture),
        "url": args.url,
        "started_utc": start_utc,
        "ended_utc": utc_now(),
        "http_status": status,
        "response_headers": headers,
        "client_ttft_seconds": first_byte_seconds,
        "client_elapsed_seconds": end - start,
        "request_sha256": sha256(body),
        "response_sha256": sha256(raw_path.read_bytes()),
        "event_count": len(events),
        "usage_objects": usage_objects,
        "timing_objects": timing_objects,
        "finish_reasons": finish_reasons,
        "output_text": "".join(output_text),
        "response_kind": "tool_call" if tool_calls_by_index else "text" if output_text else "empty",
        "tool_call_deltas": tool_call_deltas,
        "tool_calls_assembled": [tool_calls_by_index[i] for i in sorted(tool_calls_by_index)],
        "error": error,
    }
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("trial_id", "http_status", "client_elapsed_seconds", "event_count", "error")}, ensure_ascii=False))
    return 0 if status is not None and 200 <= status < 300 and error is None else 1


if __name__ == "__main__":
    raise SystemExit(main())
