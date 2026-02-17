import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    API_ACCESS_KEY = os.getenv("TENABLE_ACCESS_KEY")
    API_SECRET_KEY = os.getenv("TENABLE_SECRET_KEY")

settings = Settings()
