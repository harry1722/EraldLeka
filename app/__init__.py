import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config


app = Flask(__name__, static_folder='../static')
app.config.from_object(Config)

db = SQLAlchemy(app)
migrate = Migrate(app,db)

upload_folder = app.config['UPLOAD_FOLDER']
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])
from app import routes, models