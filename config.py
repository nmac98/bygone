import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

# Make sure .env loads locally (Render provides vars automatically)
load_dotenv()

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Get the database URL
    db_url = os.environ.get("DATABASE_URL", f"sqlite:///{BASE_DIR/'dev.db'}")

    # Fix for Render using 'postgres://' instead of 'postgresql://'
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_DATABASE_URI = db_url
