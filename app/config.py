"""
config.py
---------
Centralized configuration for the Smart Resume Screening System.

WHY THIS FILE EXISTS:
- Keeps all environment-driven settings (paths, limits, app metadata, optional
  API keys) in ONE place instead of scattering os.getenv() calls everywhere.
- Uses python-dotenv to load variables from a `.env` file at project root
  into the process environment, then wraps them in a typed Settings object.
- Other modules import `settings` from here instead of touching os.environ
  directly. This makes the app easier to test and reconfigure.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load variables from the .env file sitting at the project root into the
# environment. This MUST run before we read any os.getenv() calls below.
BASE_DIR = Path(__file__).resolve().parent.parent  # project root (one level above /app)
load_dotenv(dotenv_path=BASE_DIR / ".env")


class Settings:
    """
    Typed wrapper around environment variables.

    Every attribute here maps 1:1 to a key in the .env file. Defaults are
    provided so the app still boots even if a particular .env key is missing
    (useful for local dev / first-time setup).
    """

    # ---- App metadata ----
    APP_NAME: str = os.getenv("APP_NAME", "Smart Resume Screening System")
    APP_VERSION: str = os.getenv("APP_VERSION", "1.0.0")
    APP_ENV: str = os.getenv("APP_ENV", "development")  # development | production

    # ---- Server ----
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "True").lower() == "true"

    # ---- File upload handling ----
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads"))
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
    ALLOWED_EXTENSIONS: tuple = (".pdf",)

    # ---- Matching engine tuning ----
    # Minimum score (%) below which we still return a result but flag it as a weak match.
    MIN_MATCH_THRESHOLD: int = int(os.getenv("MIN_MATCH_THRESHOLD", "40"))

    # ---- Optional: LLM-powered explanation (future upgrade hook) ----
    # The core matching/explanation logic in this project is fully rule-based
    # (TF-IDF + regex) and works WITHOUT any of these keys. They are wired in
    # here only so that explanation_generator.py can optionally call an LLM
    # for a more natural-language explanation if a key is present.
    # Mistral is used as the open-source LLM option (via Mistral's API or a
    # self-hosted/open-weight Mistral model) instead of a closed-source
    # OpenAI model.
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    MISTRAL_API_KEY: str = os.getenv("MISTRAL_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    USE_LLM_EXPLANATION: bool = os.getenv("USE_LLM_EXPLANATION", "False").lower() == "true"

    # ---- CORS ----
    ALLOWED_ORIGINS: list = os.getenv("ALLOWED_ORIGINS", "*").split(",")


# Singleton settings instance imported across the app: `from app.config import settings`
settings = Settings()

# Ensure the upload directory always exists at startup.
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)