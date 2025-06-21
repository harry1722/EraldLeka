import os
from flask import (
    abort, render_template, request, flash, redirect, send_from_directory, 
    session, url_for, jsonify
)
from app import app, db
from app.models import Message, Project, File
from app.forms import LoginForm, ContactForm, ProjectForm
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from datetime import datetime
import logging,shutil
from app.decoraters import admin_required


load_dotenv()

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

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
    msg.read = not msg.read
    db.session.commit()
    return jsonify({'success':True,'read':msg.read})
    


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
    all_projects = Project.query.all()
    return render_template('projects.html', projects=all_projects)

@app.route('/project/<int:project_id>')
def project_detail(project_id):
    project = Project.query.get_or_404(project_id)
    files = File.query.filter_by(project_id=project.id).all()
    file_structure = build_file_structure(files)  # kjo funksion duhet të jetë në një utils/helper file
    return render_template('project_detail.html', project=project, file_structure=file_structure)

@app.route('/upload', methods=['POST'])
def upload_project():
    # merr title, description dhe file nga forma
    title = request.form.get('title')
    description = request.form.get('description')
    files = request.files.getlist('files[]')  # vjen si multiple

    # krijo projektin
    project = Project(title=title, description=description)
    db.session.add(project)
    db.session.commit()

    for file in files:
        filename = file.filename.replace("\\", "/")  # për ndarjen e folderave
        save_path = os.path.join(app.static_folder, 'uploads', filename)
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        file.save(save_path)


        # ruaj në DB
        file_entry = File(project_id=project.id, filename=filename)
        db.session.add(file_entry)

    db.session.commit()
    return jsonify({"message": "Project uploaded successfully."})

@app.route('/update_project/<int:project_id>', methods=['POST'])
def update_project(project_id):
    project = Project.query.get_or_404(project_id)
    project.title = request.form['title']
    project.description = request.form['description']
    db.session.commit()
    return redirect(url_for('projects'))

def build_file_structure(files):
    tree = {'folders': {}, 'files': []}
    for f in files:
        parts = f.filename.split('/')
        current = tree
        for part in parts[:-1]:  # gjithë folderat
            current = current['folders'].setdefault(part, {'folders': {}, 'files': []})
        # Shto path-in relative i plotë të file-it në 'files' list në këtë folder
        current['files'].append(f.filename)
    return tree


@app.route('/delete_project/<int:project_id>', methods=['DELETE'])
@admin_required
def delete_project(project_id):
    project = Project.query.get(project_id)
    if not project:
        return jsonify({'success':False,"error":'Project not found'})
    
    try:
        project_folder = os.path.join(app.static_folder,'uploads', str(project_id))
        if os.path.exists(project_folder):
            shutil.rmtree(project_folder)

        File.query.filter_by(project_id=project.id).delete()
        db.session.delete(project)
        db.session.commit()

        return jsonify({'success':True})
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error deleting project {project_id}:{e}")
        return jsonify({'success':False, 'error':'DB error'}), 500
