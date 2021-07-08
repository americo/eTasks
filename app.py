from flask import Blueprint, render_template, request, url_for, redirect, flash
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from .models import Task, User
from . import db

main = Blueprint('main', __name__)

@main.route('/')
def index():
    return redirect(url_for('auth.login'))

@main.route('/profile')
@login_required
def profile():
    return render_template('profile.html')

@main.route('/profile/edit', methods=['POST'])
@login_required
def profile_edit():
    email = request.form.get('email')
    name = request.form.get('name')
    csrf_token = request.form.get('csrf_token')
    user = User.query.filter_by(id=current_user.id).first()

    if not user.csrf_token == csrf_token:
        return "<h2>Token Anti-CSRF inválido.</h2>"
        
    user.name = name
    user.email = email
    db.session.commit()

    return redirect(url_for('main.profile'))

@main.route('/profile/security', methods=['POST'])
@login_required
def profile_security_edit():
    new_password = request.form.get('new_password')
    confirm_new_password = request.form.get('confirm_new_password')
    csrf_token = request.form.get('csrf_token')

    try:
        userForToken = User.query.filter_by(csrf_token=csrf_token).first()
    except:
        pass
    
    if not userForToken:
        return "<h2>Token Anti-CSRF inválido.</h2>"

    user = User.query.filter_by(id=current_user.id).first()

    if new_password != confirm_new_password:
        return render_template('profile.html', change_password_failed=True)
    
    user.password = generate_password_hash(new_password, method='sha256')
    db.session.commit()

    return render_template('profile.html', change_password_successfull=True)

@main.route('/delete-account', methods=['GET'])
@login_required
def delete_account():
    user = User.query.filter_by(id=current_user.id).first()
    db.session.delete(user)
    db.session.commit()

    return redirect(url_for('auth.register'))

@main.route('/dashboard')
@login_required
def dashboard():
    tasks = Task.query.filter_by(user_id=current_user.id)
    all_tasks = []
    for task in tasks:
        all_tasks.append(task)

    total_tasks = len(all_tasks)

    return render_template('dashboard.html', tasks=all_tasks, total_tasks=total_tasks)

@main.route('/add-task', methods=['POST'])
@login_required
def add_task_post():
    # create new task with the form data.
    title = request.form.get('title')
    csrf_token = request.form.get('csrf_token')
    new_task = Task(title=title, user_id=current_user.id)

    user = User.query.filter_by(id=current_user.id).first()
    
    if isinstance(csrf_token, str) == False:
        # add the new task to the database
        db.session.add(new_task)
        db.session.commit()
    elif user.csrf_token != csrf_token:
        return "<h2>Token Anti-CSRF inválido.</h2>"
    else:
        # add the new task to the database
        db.session.add(new_task)
        db.session.commit()

    return redirect(url_for('main.dashboard'))

@main.route('/delete-task', methods=['GET', 'POST'])
@login_required
def delete_task():
    if request.method == 'GET':
        task_id = request.args.get('id', '')
        csrf_token = request.args.get('csrf_token', '')
        user = User.query.filter_by(id=current_user.id).first()
        if user.csrf_token != csrf_token:
            return "<h2>Token Anti-CSRF inválido.</h2>"
    elif request.method == 'POST':
        task_id = request.form.get('id')
    
    task = Task.query.filter_by(id=task_id).first()
    if task:
        db.session.delete(task)
        db.session.commit()

    user = User.query.filter_by(id=current_user.id).first()
    user.done_tasks = user.done_tasks + 1
    db.session.commit()

    return redirect(url_for('main.dashboard'))
