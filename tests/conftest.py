import os
import sys
import tempfile
from pathlib import Path

# Make `app` importable and pin the environment BEFORE any app module import.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(
    tempfile.gettempdir(), "market_intel_test.db"
)
os.environ["CACHE_FILE"] = os.path.join(tempfile.gettempdir(), "market_intel_test_cache.json")
os.environ["AI_API_KEY"] = ""  # force template mode in tests
os.environ["MOOMOO_HOST"] = "127.0.0.1"
os.environ["MOOMOO_PORT"] = "11111"
