"""CSV tracker for job applications.

All writes go through a single asyncio.Lock so the parallel subagents
(whose tool calls run in this process) never interleave rows.
"""

import asyncio
import csv
import re
import uuid
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from . import config

FIELDS = [
    "job_id",
    "date_found",
    "company",
    "role",
    "location",
    "work_mode",
    "status",
    "url",
    "source",
    "language",
    "deadline",
    "apply_method",
    "letter_path",
    "agent_id",
    "notes",
]

STATUSES = [
    "ready_for_review",
    "approved",
    "applied",
    "interview",
    "rejected",
    "offer",
    "skipped",
]

WORK_MODES = ["hybrid", "remote", "on-site", "unknown"]

_lock = asyncio.Lock()


def normalize_url(url: str) -> str:
    """Drop query/fragment and trailing slash so tracking params don't defeat dedupe."""
    parts = urlsplit(url.strip())
    path = parts.path.rstrip("/")
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, "", ""))


def read_rows(csv_path: Path = config.CSV_PATH) -> list[dict]:
    if not csv_path.exists():
        return []
    with csv_path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _write_rows(rows: list[dict], csv_path: Path) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = csv_path.with_suffix(".tmp")
    with tmp.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    tmp.replace(csv_path)


def is_tracked(url: str, csv_path: Path = config.CSV_PATH) -> bool:
    target = normalize_url(url)
    return any(normalize_url(r["url"]) == target for r in read_rows(csv_path))


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40]


async def add_application(
    *,
    company: str,
    role: str,
    location: str,
    work_mode: str,
    url: str,
    source: str,
    language: str,
    deadline: str,
    apply_method: str,
    cover_letter: str,
    agent_id: str,
    notes: str = "",
    csv_path: Path = config.CSV_PATH,
    letters_dir: Path = config.LETTERS_DIR,
) -> dict:
    """Save the cover letter and append a row. Returns the row, or raises ValueError on duplicate."""
    async with _lock:
        rows = read_rows(csv_path)
        target = normalize_url(url)
        if any(normalize_url(r["url"]) == target for r in rows):
            raise ValueError(f"Already tracked: {url}")

        job_id = f"{_slug(company)}-{uuid.uuid4().hex[:6]}"
        letters_dir.mkdir(parents=True, exist_ok=True)
        letter_path = letters_dir / f"{job_id}.md"
        letter_path.write_text(cover_letter, encoding="utf-8")

        mode = work_mode.lower().strip()
        row = {
            "job_id": job_id,
            "date_found": date.today().isoformat(),
            "company": company,
            "role": role,
            "location": location,
            "work_mode": mode if mode in WORK_MODES else "unknown",
            "status": "ready_for_review",
            "url": url,
            "source": source,
            "language": language,
            "deadline": deadline,
            "apply_method": apply_method,
            "letter_path": str(letter_path.relative_to(config.ROOT))
            if letter_path.is_relative_to(config.ROOT)
            else str(letter_path),
            "agent_id": agent_id,
            "notes": notes,
        }
        rows.append(row)
        _write_rows(rows, csv_path)
        return row


def set_status(job_id: str, status: str, csv_path: Path = config.CSV_PATH) -> dict:
    if status not in STATUSES:
        raise ValueError(f"Unknown status {status!r}; use one of {STATUSES}")
    rows = read_rows(csv_path)
    for row in rows:
        if row["job_id"] == job_id:
            row["status"] = status
            _write_rows(rows, csv_path)
            return row
    raise KeyError(f"No job with id {job_id!r}")
