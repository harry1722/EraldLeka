import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config
import logging
from logging.handlers import RotatingFileHandler


app = Flask(__name__, static_folder='../static')
app.config.from_object(Config)

db = SQLAlchemy(app)
migrate = Migrate(app,db)

upload_folder = app.config['UPLOAD_FOLDER']
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])


#logging set up
if not os.path.exists('logs'):
    os.makedirs('logs')

file_handler = RotatingFileHandler('logs/app.log', maxBytes=10240, backupCount=5)
file_handler.setFormatter(logging.Formatter(
    '[%(asctime)s] %(levelname)s im %(module)s: %(message)s'
))
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)
app.logger.info('App startup')


from app import routes, models