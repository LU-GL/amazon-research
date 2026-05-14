import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SELLER_JING_DIR = DATA_DIR / "seller_jing"
AMAZON_EXPORTS_DIR = DATA_DIR / "amazon_exports"
RAW_LISTINGS_DIR = DATA_DIR / "raw_listings"
RAW_REVIEWS_DIR = DATA_DIR / "raw_reviews"
OUTPUT_DIR = PROJECT_ROOT / "output"
DB_PATH = DATA_DIR / "amazon_research.db"

for d in [DATA_DIR, SELLER_JING_DIR, AMAZON_EXPORTS_DIR, RAW_LISTINGS_DIR, RAW_REVIEWS_DIR, OUTPUT_DIR]:
    d.mkdir(parents=True, exist_ok=True)

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL")
MODEL = "mimo-v2-pro"
