"""Run main.py in a background process so the UI stays responsive.

The process handle lives at module level: Streamlit imports this module once
per server, so the handle survives page reruns and navigation.
"""

import os
import subprocess
import sys
import time
from dataclasses import dataclass

from . import config

LOG_PATH = config.OUTPUT_DIR / "last_run.log"


@dataclass
class Run:
    process: subprocess.Popen
    label: str
    started: float


_current: Run | None = None


def start(label: str, *args: str) -> None:
    """Start `python main.py <args> --yes`. Raises RuntimeError if a run is active."""
    global _current
    if is_running():
        raise RuntimeError("A run is already in progress.")
    config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    log = LOG_PATH.open("w", encoding="utf-8")
    process = subprocess.Popen(
        [sys.executable, "-u", str(config.ROOT / "main.py"), *args, "--yes"],
        cwd=config.ROOT,
        stdout=log,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    log.close()  # the child keeps its own handle
    _current = Run(process, label, time.time())


def is_running() -> bool:
    return _current is not None and _current.process.poll() is None


def current() -> Run | None:
    return _current


def stop() -> None:
    if is_running():
        _current.process.terminate()


def read_log() -> str:
    return LOG_PATH.read_text(encoding="utf-8", errors="replace") if LOG_PATH.exists() else ""
