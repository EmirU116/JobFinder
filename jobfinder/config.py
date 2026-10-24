from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DATA_DIR = ROOT / "data"
CV_PATH = DATA_DIR / "cv.pdf"
PROFILE_PATH = DATA_DIR / "profile.json"

OUTPUT_DIR = ROOT / "output"
CSV_PATH = OUTPUT_DIR / "applications.csv"
LETTERS_DIR = OUTPUT_DIR / "letters"

# Lead agent model; subagents inherit it unless SUBAGENT_MODEL is changed.
MODEL = "claude-opus-5-5"
SUBAGENT_MODEL = "inherit"

NUM_AGENTS = 3
JOBS_PER_AGENT = 5

# Guardrails for one full run (phase 2).
MAX_BUDGET_USD = 15.0
MAX_TURNS = 200
