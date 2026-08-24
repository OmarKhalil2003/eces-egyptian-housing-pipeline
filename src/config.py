from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
import os

ALGOLIA_APP_ID = os.getenv(
    "ALGOLIA_APP_ID",
    "LL8IZ711CS",
)

ALGOLIA_SEARCH_API_KEY = os.getenv(
    "ALGOLIA_SEARCH_API_KEY",
)

ALGOLIA_SALE_INDEX = (
    "bayut-eg-production-ads-city-level-score-ar"
)
# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
OUTPUT_DIR = DATA_DIR / "output"
EVALUATION_DIR = BASE_DIR / "evaluation"

DB_PATH = DATA_DIR / "housing_pipeline.db"

DATASET_XLSX = OUTPUT_DIR / "egypt_housing_market_dataset.xlsx"
DATASET_CSV = OUTPUT_DIR / "egypt_housing_market_dataset.csv"
DATASET_JSONL = OUTPUT_DIR / "egypt_housing_market_dataset.jsonl"


# ---------------------------------------------------------------------------
# Bayut
# ---------------------------------------------------------------------------

BASE_URL = "https://www.bayut.eg"

# We start with the broad category pages.
# Exact URL structures can be adjusted after inspecting Bayut's live HTML.
SALE_URL = f"{BASE_URL}/en/egypt/properties-for-sale/"
RENT_URL = f"{BASE_URL}/en/egypt/properties-for-rent/"


# ---------------------------------------------------------------------------
# Collection
# ---------------------------------------------------------------------------

TARGET_COUNT = 550

# Number of listings we want to attempt to collect before considering
# the collection complete.
MIN_REQUIRED_LISTINGS = 500

# Maximum number of consecutive failed requests before stopping a run.
MAX_CONSECUTIVE_FAILURES = 10

# HTTP behavior.
REQUEST_TIMEOUT = 30.0
MAX_RETRIES = 3

# Delay between requests. Keep this configurable rather than hard-coding
# sleeps inside the collector.
MIN_REQUEST_DELAY = 2.0
MAX_REQUEST_DELAY = 3.0


# ---------------------------------------------------------------------------
# HTTP headers
# ---------------------------------------------------------------------------

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/150.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9,ar;q=0.8",
    "Connection": "keep-alive",
}


# ---------------------------------------------------------------------------
# Scope
# ---------------------------------------------------------------------------

# These are the governorates we intend to cover.
# The collector should verify that the resulting dataset actually contains
# listings from at least three governorates.
TARGET_GOVERNORATES = {
    "Cairo",
    "Giza",
    "Alexandria",
    "Red Sea",
}


# ---------------------------------------------------------------------------
# Extraction categories
# ---------------------------------------------------------------------------

FINISHING_LEVELS = {
    "core & shell",
    "semi-finished",
    "fully finished",
    "super lux",
    "furnished",
    "unknown",
}

DELIVERY_STATUSES = {
    "ready",
    "off-plan",
}

SALE_TYPES = {
    "primary",
    "resale",
}

PAYMENT_TYPES = {
    "cash",
    "installments",
    "both",
}

INSTALLMENT_FREQUENCIES = {
    "monthly",
    "quarterly",
    "annual",
}


# ---------------------------------------------------------------------------
# Runtime directories
# ---------------------------------------------------------------------------

def ensure_directories() -> None:
    """
    Create required project directories if they do not already exist.
    """
    for directory in (
        DATA_DIR,
        RAW_DIR,
        OUTPUT_DIR,
        EVALUATION_DIR,
    ):
        directory.mkdir(parents=True, exist_ok=True)