"""
config/settings.py
──────────────────
Single source of truth for all configuration values.
Loads from .env using python-dotenv and exposes typed constants.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the project root (one level up from config/)
_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")

def _require(key: str) -> str:
    """Return env var value or raise a clear error if it's missing"""
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(
            f"Required environment variable '{key}' isn't set"
            f"Check your .env file against .env.example"
        )
    return value

def _int(key: str, default: int) -> int:
    """Return env var as int, with a default fallback"""
    return int(os.getenv(key, default))

# ── API ───────────────────────────────────────────────────────────────────────
BASE_URL: str = _require("BASE_URL")
API_PREFIX: str = os.getenv("API_PREFIX", "/api")
BASE_API_URL: str = f"{BASE_URL}{API_PREFIX}"

# ── Timeouts ─────────────────────────────────────────────────────────────────
REQUEST_TIMEOUT_MS: int = _int("REQUEST_TIMEOUT_MS", 10_000)
MAX_RESPONSE_TIME_MS: int = _int("MAX_RESPONSE_TIME_MS", 3_000)

# ── Auth credentials ─────────────────────────────────────────────────────────
TEST_EMAIL: str = _require("TEST_EMAIL")
TEST_PASSWORD: str = _require("TEST_PASSWORD")

# ── Reporting ─────────────────────────────────────────────────────────────────
ALLURE_RESULTS_DIR: str = os.getenv("ALLURE_RESULTS_DIR", "allure-results")