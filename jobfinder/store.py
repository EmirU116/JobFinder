"""CSV tracker for job applications.

Writes are serialized twice: an asyncio.Lock for the parallel subagents
(whose tool calls run in one process), and a lock file so the Streamlit UI
and an agent run in separate processes never overwrite each other's rows.
"""

import asyncio
import csv
import os
import re
import time
import uuid
from contextlib import contextmanager
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

# Fields the UI may edit; everything else is written only by the agents.
EDITABLE_FIELDS = {"status", "notes", "deadline", "work_mode", "apply_method"}

_lock = asyncio.Lock()
_STALE_LOCK_SECONDS = 30


@contextmanager
def _file_lock(csv_path: Path, timeout: float = 10.0):
    """Cross-process lock: exclusive creation of <csv>.lock."""
    lock_path = csv_path.with_suffix(".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout
    while True:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            try:
                if time.time() - lock_path.stat().st_mtime > _STALE_LOCK_SECONDS:
                    lock_path.unlink(missing_ok=True)  # left behind by a crashed process
                    continue
            except FileNotFoundError:
                continue
            if time.monotonic() > deadline:
                raise TimeoutError(f"Could not lock {csv_path}")
            time.sleep(0.05)
    try:
        yield
    finally:
        os.close(fd)
        lock_path.unlink(missing_ok=True)


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
    async with _lock, _file_lock_async(csv_path):
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


class _AsyncFileLock:
    def __init__(self, csv_path: Path):
        self._cm = _file_lock(csv_path)

    async def __aenter__(self):
        # Contention is rare and the critical section is milliseconds, so a blocking wait is fine.
        return self._cm.__enter__()

    async def __aexit__(self, *exc):
        return self._cm.__exit__(*exc)


def _file_lock_async(csv_path: Path) -> _AsyncFileLock:
    return _AsyncFileLock(csv_path)


def update_row(job_id: str, csv_path: Path = config.CSV_PATH, **fields: str) -> dict:
    """Update UI-editable fields of one job. Raises KeyError/ValueError on bad input."""
    unknown = set(fields) - EDITABLE_FIELDS
    if unknown:
        raise ValueError(f"Fields not editable: {sorted(unknown)}")
    if "status" in fields and fields["status"] not in STATUSES:
        raise ValueError(f"Unknown status {fields['status']!r}; use one of {STATUSES}")
    if "work_mode" in fields and fields["work_mode"] not in WORK_MODES:
        raise ValueError(f"Unknown work mode {fields['work_mode']!r}; use one of {WORK_MODES}")
    with _file_lock(csv_path):
        rows = read_rows(csv_path)
        for row in rows:
            if row["job_id"] == job_id:
                row.update(fields)
                _write_rows(rows, csv_path)
                return row
    raise KeyError(f"No job with id {job_id!r}")


def set_status(job_id: str, status: str, csv_path: Path = config.CSV_PATH) -> dict:
    return update_row(job_id, csv_path, status=status)


def letter_file(row: dict) -> Path:
    path = Path(row["letter_path"])
    return path if path.is_absolute() else config.ROOT / path


def read_letter(row: dict) -> str:
    path = letter_file(row)
    return path.read_text(encoding="utf-8") if path.exists() else ""


def write_letter(row: dict, text: str) -> None:
    path = letter_file(row)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
