import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

BASE_URL = os.getenv("BASE_URL", "https://clove-vinculo.onrender.com").rstrip("/")
PORT = int(os.getenv("PORT", "5000"))
SESSION_SECRET = os.getenv("SESSION_SECRET", "dev-secret")

DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET")
DISCORD_REDIRECT_URI = os.getenv("DISCORD_REDIRECT_URI", "https://clove-vinculo.onrender.com/callback")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DISCORD_GUILD_ID = os.getenv("DISCORD_GUILD_ID")

HENRIK_API_KEY = os.getenv("HENRIK_API_KEY")

DATABASE_PATH = BASE_DIR / "link_system.db"

DEFAULT_REGION = "br"

RANK_ROLE_MAP = {
    "Iron": "Iron",
    "Bronze": "Bronze",
    "Silver": "Silver",
    "Gold": "Gold",
    "Platinum": "Platinum",
    "Diamond": "Diamond",
    "Ascendant": "Ascendant",
    "Immortal": "Immortal",
    "Radiant": "Radiant",
}

ALL_TRACKED_ROLE_NAMES = list(RANK_ROLE_MAP.values())
