from app import db
from datetime import datetime

# --- Messages që vijnë nga forma e kontaktit ---
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    profession = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    time = db.Column(db.DateTime, default=datetime.utcnow)

# --- Project Model ---
class Project(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100))
    description = db.Column(db.Text)

    # Relationship me File modelin
    files = db.relationship(
        'File',
        backref='project',
        cascade='all, delete-orphan',  # Fshin edhe file-at nëse fshihet projekti
        lazy=True
    )

# --- File Model ---
class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(200))  # Emri + rruga relative (p.sh. 'folder1/test.py')
    upload_time = db.Column(db.DateTime, default=datetime.utcnow)

    # Foreign key që lidh file-in me projektin
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
