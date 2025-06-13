import os
from flask import abort, render_template, request, flash, redirect, send_from_directory, session, url_for
from app import app, db
from app.models import Message, Project, File
from app.forms import LoginForm, ContactForm, ProjectForm
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from datetime import datetime

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
def messages():
    if session.get('user') != 'admin':
        flash("Access denied", "danger")
        return redirect(url_for('login'))
    messages = Message.query.order_by(Message.time.desc()).all()
    return render_template('messages.html', messages=messages)

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


# --------- PROJECTS ROUTES START ---------

@app.route('/projects', methods=['GET', 'POST'])
def projects():
    form = ProjectForm()
    if form.validate_on_submit():
        if session.get('user') != 'admin':
            flash('Access denied', 'danger')
            return redirect(url_for('projects'))

        title = form.title.data
        description = form.description.data
        uploaded_files = request.files.getlist('folder[]')

        if not uploaded_files or any(file.filename == '' or not allowed_file(file.filename) for file in uploaded_files):
            flash("Only certain file types are allowed and files must have a name!", "danger")
            return redirect(url_for('projects'))

        upload_folder = app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)

        new_project = Project(title=title, description=description)
        db.session.add(new_project)
        db.session.flush()  # get id before commit

        for file in uploaded_files:
            safe_path = os.path.normpath(file.filename)
            if safe_path.startswith('..'):
                flash("Invalid file path detected!", "danger")
                return redirect(url_for('projects'))

            full_path = os.path.join(upload_folder, safe_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            file.save(full_path)

            file_obj = File(filename=safe_path, project_id=new_project.id)
            db.session.add(file_obj)

        try:
            db.session.commit()
            flash("Project added successfully!", 'success')
        except Exception as e:
            db.session.rollback()
            flash("Failed to add project. Try again", 'danger')
            print(f"DB Error: {e}")
        return redirect(url_for('projects'))

    all_projects = Project.query.order_by(Project.id.desc()).all()
    return render_template('projects.html', projects=all_projects, form=form)


@app.route('/projects/edit/<int:project_id>', methods=['GET', 'POST'])
def edit_project(project_id):
    if session.get('user') != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('projects'))

    project = Project.query.get_or_404(project_id)
    form = ProjectForm(obj=project)

    if form.validate_on_submit():
        project.title = form.title.data
        project.description = form.description.data
        db.session.commit()
        flash('Project updated!', 'success')
        return redirect(url_for('projects'))

    return render_template('edit_project.html', form=form, project=project)


@app.route('/projects/delete/<int:project_id>')
def delete_project(project_id):
    if session.get('user') != 'admin':
        flash('Access denied', 'danger')
        return redirect(url_for('projects'))

    project = Project.query.get_or_404(project_id)
    try:
        upload_folder = app.config['UPLOAD_FOLDER']
        for f in project.files:
            fpath = os.path.join(upload_folder, f.filename)
            if os.path.exists(fpath):
                os.remove(fpath)
        db.session.delete(project)
        db.session.commit()
        flash('Project deleted!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Failed to delete project!', 'danger')
        print(f"Error deleting project: {e}")

    return redirect(url_for('projects'))


def insert_into_tree(tree, path):
    parts = path.split('/', 1)
    if len(parts) == 1:
        tree.setdefault('files', []).append(parts[0])
    else:
        folder, rest = parts
        if 'folders' not in tree:
            tree['folders'] = {}
        if folder not in tree['folders']:
            tree['folders'][folder] = {'folders': {}, 'files': []}
        insert_into_tree(tree['folders'][folder], rest)
    return tree


def build_file_structure(files):
    tree = {'folders': {}, 'files': []}
    for f in files:
        insert_into_tree(tree, f.filename)
    return tree


@app.route('/download/<int:project_id>/<path:filename>')
def download_file(project_id, filename):
    project = Project.query.get_or_404(project_id)
    if not any(f.filename == filename for f in project.files):
        abort(404)

    upload_folder = app.config['UPLOAD_FOLDER']
    file_path = os.path.join(upload_folder, filename)

    if not os.path.isfile(file_path):
        abort(404)

    return send_from_directory(directory=upload_folder, path=filename, as_attachment=True)


@app.route('/project_detail/<int:project_id>')
def project_detail(project_id):
    project = Project.query.get_or_404(project_id)
    file_structure = build_file_structure(project.files)
    return render_template('project_detail.html', project=project, file_structure=file_structure)

# --------- PROJECTS ROUTES END ---------
