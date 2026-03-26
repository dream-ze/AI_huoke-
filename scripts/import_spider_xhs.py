#!/usr/bin/env python3
"""Batch import Spider_XHS output into 智获客 /api/v2/collect/ingest-spider-xhs/batch.

Usage:
  python scripts/import_spider_xhs.py \
    --api-base http://116.62.86.160:8000 \
    --token <ACCESS_TOKEN> \
    --input-dir D:\\Spider_XHS\\datas
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import requests


def _iter_info_json(input_dir: Path) -> Iterable[Path]:
    for p in input_dir.rglob("info.json"):
        if p.is_file():
            yield p


def _chunked(items: list[dict], size: int) -> Iterable[list[dict]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _load_note(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    if not text:
        return {}
    # Spider_XHS usually stores a single JSON object per info.json.
    # If multiple lines exist, try the first valid JSON object.
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                continue
    return {}


def _to_payload(note: dict) -> dict:
    return {
        "note_id": str(note.get("note_id", "")),
        "note_url": note.get("note_url") or note.get("url"),
        "note_type": note.get("note_type"),
        "title": note.get("title"),
        "desc": note.get("desc") or note.get("description"),
        "nickname": note.get("nickname") or note.get("author"),
        "upload_time": note.get("upload_time") or note.get("publish_time"),
        "tags": note.get("tags") or [],
        "liked_count": int(note.get("liked_count", note.get("likes", 0)) or 0),
        "collected_count": int(note.get("collected_count", note.get("collects", 0)) or 0),
        "comment_count": int(note.get("comment_count", note.get("comments", 0)) or 0),
        "share_count": int(note.get("share_count", note.get("shares", 0)) or 0),
        "image_list": note.get("image_list") or [],
        "video_cover": note.get("video_cover"),
        "video_addr": note.get("video_addr"),
        "raw_payload": note,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Import Spider_XHS output into 智获客")
    parser.add_argument("--api-base", required=True, help="e.g. http://116.62.86.160:8000")
    parser.add_argument("--token", required=True, help="Bearer token value (without 'Bearer ')")
    parser.add_argument("--input-dir", required=True, help="Spider_XHS data directory")
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--batch-size", type=int, default=50, help="items per request, max 200")
    args = parser.parse_args()

    api_base = args.api_base.rstrip("/")
    endpoint = f"{api_base}/api/v2/collect/ingest-spider-xhs/batch"
    headers = {
        "Authorization": f"Bearer {args.token}",
        "Content-Type": "application/json",
    }

    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        print(f"[ERROR] input dir not found: {input_dir}")
        return 2

    total = 0
    ok = 0
    dedupe = 0
    failed = 0
    payload_items: list[dict] = []

    for info_file in _iter_info_json(input_dir):
        note = _load_note(info_file)
        if not note:
            failed += 1
            print(f"[FAIL] {info_file} -> empty/invalid json")
            continue

        payload = _to_payload(note)
        if not payload.get("note_id"):
            failed += 1
            print(f"[FAIL] {info_file} -> missing note_id")
            continue
        total += 1
        payload_items.append(payload)

    if not payload_items:
        print("[INFO] no valid notes to import")
        print("\n=== SUMMARY ===")
        print(f"total={total} ok={ok} dedupe={dedupe} failed={failed}")
        return 0 if failed == 0 else 1

    batch_size = max(1, min(int(args.batch_size or 50), 200))
    for index, batch in enumerate(_chunked(payload_items, batch_size), start=1):
        try:
            resp = requests.post(endpoint, headers=headers, json={"items": batch}, timeout=args.timeout)
            if resp.status_code != 200:
                failed += len(batch)
                print(f"[FAIL] batch#{index} -> HTTP {resp.status_code}: {resp.text[:240]}")
                continue
            data = resp.json()
            ok += int(data.get("ok", 0) or 0)
            dedupe += int(data.get("dedupe", 0) or 0)
            batch_failed = int(data.get("failed", 0) or 0)
            failed += batch_failed
            print(
                f"[OK] batch#{index} total={data.get('total')} "
                f"ok={data.get('ok')} dedupe={data.get('dedupe')} failed={data.get('failed')}"
            )
            for row in data.get("rows", []):
                if row.get("status") == "failed":
                    print(f"  [ROW-FAIL] note_id={row.get('note_id')} error={row.get('error')}")
        except Exception as exc:  # noqa: BLE001
            failed += len(batch)
            print(f"[FAIL] batch#{index} -> {exc}")

    print("\n=== SUMMARY ===")
    print(f"total={total} ok={ok} dedupe={dedupe} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
