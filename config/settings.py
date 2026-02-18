import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

class Settings:
    APP_ENV: str = os.getenv("APP_ENV", "development")
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    MOCK_MODE: bool = os.getenv("MOCK_MODE", "true").lower() == "true"
    TENABLE_ACCESS_KEY: str = os.getenv("TENABLE_ACCESS_KEY", "")
    TENABLE_SECRET_KEY: str = os.getenv("TENABLE_SECRET_KEY", "")
    TENABLE_API_URL: str = os.getenv("TENABLE_API_URL", "https://cloud.tenable.com")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")
    REPORT_OUTPUT_DIR: Path = Path(os.getenv("REPORT_OUTPUT_DIR", "./reports"))
    CUSTOMER_NAME: str = os.getenv("CUSTOMER_NAME", "Unknown Customer")
    ENGAGEMENT_ID: str = os.getenv("ENGAGEMENT_ID", "ENG-000")
    VERSION: str = "1.0.0"
    APP_NAME: str = "MPIV TVM Advisor"

    @classmethod
    def validate(cls) -> list:
        warnings = []
        if cls.MOCK_MODE:
            warnings.append("MOCK MODE active — no real Tenable API calls.")
        if not cls.OPENAI_API_KEY:
            warnings.append("OPENAI_API_KEY not set — AI narrative disabled.")
        return warnings

    @classmethod
    def is_openai_configured(cls) -> bool:
        return bool(cls.OPENAI_API_KEY)

settings = Settings()