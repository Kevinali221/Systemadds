from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
INPUT_DIR = BASE_DIR / "input"
OUTPUT_DIR = BASE_DIR / "output"
LOGO_PATH = ASSETS_DIR / "logo.png"

VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

BUSINESS_NAME = "D&A E-Mechanic LLC"
ADDRESS = "2596 Michigan Ave, Ste C, Kissimmee, FL 34744"
PHONES = ["(863) 335-7429", "(352) 809-7328"]

COLORS = {
    "primary": "#0A84FF",
    "navy": "#0A1A3A",
    "dark": "#0B0B0F",
    "surface": "#1C1C22",
    "white": "#FFFFFF",
}

FORMATS = {
    "story": (1080, 1920),  # 9:16 Stories / WhatsApp
    "feed": (1080, 1350),   # 4:5 Feed
}
