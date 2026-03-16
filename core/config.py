import os
from dotenv import load_dotenv

# Load environment variables from the .env file into os.environ
load_dotenv()

class Settings:
    # 1. AI Provider Keys
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

    # 2. PostgreSQL Database Credentials
    DB_NAME = os.getenv("DB_NAME", "stockmind_db")
    DB_USER = os.getenv("DB_USER", "postgres")
    DB_PASS = os.getenv("DB_PASS", "")
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = os.getenv("DB_PORT", "5432")

    # 3. Email Alert System (SMTP)
    SMTP_EMAIL = os.getenv("SMTP_EMAIL")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
    ALERT_EMAIL = os.getenv("ALERT_EMAIL")

    # 4. System Configuration
    PORT = int(os.getenv("PORT", 8000))
    MORNING_HOUR = os.getenv("MORNING_HOUR", "08:00")

# Instantiate the settings so it can be imported cleanly across the app
settings = Settings()
