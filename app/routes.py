import os
from flask import (
    abort, render_template, request, flash, redirect, send_from_directory, 
    session, url_for, jsonify
)
from app import app, db
from app.models import Message, Project
from app.forms import LoginForm, ContactForm, ProjectForm
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from datetime import datetime
import logging,shutil
from app.decoraters import admin_required
from io import BytesIO
from supabase import create_client
import time


load_dotenv()

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt', 'png', 'jpg', 'jpeg', 'zip', 'py', 'html', 'css', 'js'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        try:
            new_message = Message(
                name=form.name.data,
                profession=form.profession.data,
                message=form.message.data
            )
            db.session.add(new_message)
            db.session.commit()
            flash('I got your message. Thank you!', 'success')
            return redirect(url_for('contact'))
        except Exception as e:
            db.session.rollback()
            flash('Oops, something went wrong while saving your message. Try again!', 'danger')
            print(f"DB Error: {e}")
    return render_template('contact.html', form=form)

@app.route('/messages')
@admin_required
def messages():
    messages = Message.query.order_by(Message.time.desc()).all()
    return render_template('messages.html', messages=messages)

@app.route('/messages/toggle_read/<int:msg_id>', methods=['POST'])
@admin_required
def toggle_read(msg_id):
    msg = Message.query.get_or_404(msg_id)
    msg.is_read = not msg.is_read
    db.session.commit()
    return jsonify({'success':True,'read':msg.is_read})
    


@app.route('/messages/delete/<int:msg_id>', methods=['POST'])
@admin_required
def delete_message(msg_id):

    msg = Message.query.get(msg_id)
    if not msg:
        return jsonify({'success':False,'error':'Message not found'}),404
    
    try:
        db.session.delete(msg)
        db.session.commit()
        return jsonify({'success':True})
    except Exception as e:
        db.session.rollback()
        logging.error('Error deletin message: {e}')
        return jsonify({'success':False, 'error':'DB error'}),500

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        if form.username.data == ADMIN_USERNAME and form.password.data == ADMIN_PASSWORD:
            session['user'] = form.username.data
            flash('Welcome back, admin!', 'success')
            return redirect(url_for('home'))
        else:
            flash('Incorrect username or password', 'danger')
    return render_template("login.html", form=form)

@app.route('/logout')
def logout():
    session.pop('user', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))

@app.route('/projects')
def projects():
    projects = Project.query.all()
    for project in projects:
        if project.image:
            url_response = supabase.storage.from_('images').get_public_url(project.image)
            print('URL from Supabase:', url_response)  # Kjo duhet brenda if-it
            project.public_url = url_response
        else:
            project.public_url = None
    return render_template('projects.html', projects=projects)





@app.route('/upload', methods=['POST'])
def upload_project():
    title = request.form.get('title')
    description = request.form.get('description')
    link = request.form.get('link')
    image = request.files.get('image')

    if not title or not description or not image or not allowed_file(image.filename):
        flash('Missing required fields or invalid image', 'danger')
        return redirect(url_for('projects'))

    filename = secure_filename(image.filename)
    timestamp = int(time.time())
    filename = f"{timestamp}_{filename}"

    image_bytes = image.read()

    try:
        result = supabase.storage.from_('images').upload(filename, image_bytes)
    except Exception as e:
        flash(f'Gabim gjatë ngarkimit në Supabase: {e}', 'danger')
        return redirect(url_for('projects'))

    # Nëse arrijmë këtu, upload ka kaluar

    project = Project(title=title, description=description, link=link, image=filename)
    try:
        db.session.add(project)
        db.session.commit()
        flash('Project added successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error saving project: {e}', 'danger')

    return redirect(url_for('projects'))

@app.route('/update_project/<int:id>', methods=['POST'])
def update_project(id):
    project = Project.query.get_or_404(id)
    project.title = request.form.get('title')
    project.description = request.form.get('description')
    project.link = request.form.get('link')
    try:
        db.session.commit()
        flash('Project updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating project: {e}', 'danger')
        logging.error(f"DB update error: {e}")
    return redirect(url_for('projects'))


@app.route('/delete_project/<int:id>', methods=['DELETE'])
def delete_project(id):
    project = Project.query.get_or_404(id)
    try:
        # Nëse dëshiron mund të shtosh edhe fshirjen e fotos nga Supabase këtu
        db.session.delete(project)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error deleting project {id}: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500