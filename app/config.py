"""Runtime settings, read from .env at the repo root."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "").strip()
MISTRAL_CHAT_MODEL = os.getenv("MISTRAL_CHAT_MODEL", "mistral-medium-latest").strip()
MISTRAL_EMBED_MODEL = os.getenv("MISTRAL_EMBED_MODEL", "mistral-embed").strip()
# Source checks use a small model so they never eat the rate limit the live resident flow needs.
MISTRAL_CHECK_MODEL = os.getenv("MISTRAL_CHECK_MODEL", "mistral-small-latest").strip()
ES_URL = os.getenv("ES_URL", "").strip()
ES_API_KEY = os.getenv("ES_API_KEY", "").strip()

# Elasticsearch names (shared contract, see CONTRACT.md)
INDEX_PROGRAMS = "homebase-programs"
INDEX_APPLICATIONS = "homebase-applications"
INFERENCE_ID = "homebase-mistral-embed"
FALLBACK_INFERENCE_ID = ".multilingual-e5-small-elasticsearch"

DATA_DIR = ROOT / "app" / "data"
WEB_DIR = ROOT / "web"
