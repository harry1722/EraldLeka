import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
project_root = os.path.abspath(os.path.join(basedir, '..'))

load_dotenv(os.path.join(project_root, '.env'))

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'fallback-secret-if-not-set')

    db_url = os.getenv("DATABASE_URL")
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    SQLALCHEMY_DATABASE_URI = db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Upload folder ku ruhen fotot
    UPLOAD_FOLDER = os.path.join(project_root, 'static', 'uploads')
