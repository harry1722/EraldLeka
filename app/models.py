from app import db
from datetime import datetime
import os

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    profession = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    time = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    link = db.Column(db.String(255))
    image = db.Column(db.String(255))  # Emri i file-it të ngarkuar në Supabase bucket 'images'

    @property
    def image_url(self):
        SUPABASE_URL = os.getenv('SUPABASE_URL')
        if self.image:
            # Krijon URL publike për imazhin në bucket 'images'
            return f"{SUPABASE_URL}/storage/v1/object/public/images/{self.image}"
        return None
