import os
from flask import render_template, request, flash, redirect, session, url_for
from app import app, db
from app.models import Message, Project
from app.forms import LoginForm, ContactForm, ProjectForm
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

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

@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html'), 404

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

        saved_files = []
        for file in uploaded_files:
            # Siguro rrugën relative (sanitize)
            safe_path = os.path.normpath(file.filename)
            # Mos lejo që të kalojë jashtë folderit (p.sh ../../file)
            if safe_path.startswith('..'):
                flash("Invalid file path detected!", "danger")
                return redirect(url_for('projects'))

            full_path = os.path.join(upload_folder, safe_path)

            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            file.save(full_path)

            saved_files.append(safe_path)

        new_project = Project(
            title=title,
            description=description,
            file_names=','.join(saved_files)
        )
        try:
            db.session.add(new_project)
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
        db.session.delete(project)
        db.session.commit()
        flash('Project deleted!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Failed to delete project!', 'danger')
        print(f"Error deleting project: {e}")

    return redirect(url_for('projects'))


# --- Ndërtimi i strukturës folder + files ---

def insert_into_tree(tree, path):
    parts = path.split('/', 1)
    if len(parts) == 1:
        tree.setdefault('files', []).append(parts[0])
    else:
        folder, rest = parts
        if 'folders' not in tree:
            tree['folders'] = {}
        if folder not in tree['folders']:
            tree['folders'][folder] = {}
        insert_into_tree(tree['folders'][folder], rest)
    return tree

def build_file_structure(filenames):
    tree = {}
    for fname in filenames:
        insert_into_tree(tree, fname)
    return tree

def loop_structure(tree):
    html = ''
    if 'folders' in tree:
        for folder_name, contents in tree['folders'].items():
            html += f'<li><div class="folder" aria-expanded="false">▶ {folder_name}</div>'
            html += f'<ul class="folder-contents">{loop_structure(contents)}</ul></li>'
    if 'files' in tree:
        for file in tree['files']:
            html += f'<li class="file">{file}</li>'
    return html


@app.route('/project_detail/<int:project_id>')
def project_detail(project_id):
    project = Project.query.get_or_404(project_id)
    file_names = project.file_names.split(',') if project.file_names else []

    file_structure = build_file_structure(file_names)

    return render_template('project_detail.html',
                           project=project,
                           file_structure=file_structure,
                           loop_structure=loop_structure)
