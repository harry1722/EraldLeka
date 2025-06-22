import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config
import logging
from logging.handlers import RotatingFileHandler

basedir = os.path.abspath(os.path.dirname(__file__))
project_root = os.path.abspath(os.path.join(basedir, '..'))
static_path = os.path.join(project_root, 'static')

app = Flask(__name__, static_folder=static_path)  # FIX: use absolute static folder path
app.config.from_object(Config)
app.config['UPLOAD_FOLDER'] = os.path.join(static_path, 'uploads')


db = SQLAlchemy(app)
migrate = Migrate(app, db)

upload_folder = app.config['UPLOAD_FOLDER']
if not os.path.exists(upload_folder):
    os.makedirs(upload_folder)

if not os.path.exists('logs'):
    os.makedirs('logs')

file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=5)
file_handler.setFormatter(logging.Formatter(
    '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
))
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)
app.logger.info('App startup')

from app.decoraters import unread_count
app.context_processor(unread_count)

from app import routes, models, decoraters
