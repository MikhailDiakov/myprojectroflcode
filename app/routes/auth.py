from flask import Blueprint, render_template, request, redirect, url_for, session
from werkzeug.utils import secure_filename
import os
from ..models import User, db
import re

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/create', methods=['GET', 'POST'])
def create():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if len(username) < 3 or len(username) > 20:
            error_message = 'Username must be between 3 and 20 characters.'
            return render_template('auth/create.html', error_message=error_message, username=username, email=email)
        
        email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        if not re.match(email_regex, email) or len(email) > 255:
            error_message = 'Invalid email address format.'
            return render_template('auth/create.html', error_message=error_message, username=username, email=email)
        
        if len(password) < 8 or len(password) > 20:
            error_message = 'Password must be between 8 and 20 characters.'
            return render_template('auth/create.html', error_message=error_message, username=username, email=email)
        
        if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
            error_message = 'Username or email already exists.'
            return render_template('auth/create.html', error_message=error_message, username=username, email=email)

        if password != confirm_password:
            error_message = 'Passwords do not match.'
            return render_template('auth/create.html', error_message=error_message)

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        session['user_id'] = user.id
        session['username'] = user.username
        session['avatar_url'] = user.avatar_url
        return redirect(url_for('main.index'))

    return render_template('auth/create.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('main.index'))

        error_message = 'Invalid username or password.'
        return render_template('auth/login.html', error_message=error_message)

    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.index'))

@auth_bp.route('/profile/<username>')
def user_profile(username):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    user = User.query.filter_by(username=username).first_or_404()
    articles = user.articles
    avatar_url=user.avatar_url
    return render_template('auth/profile.html', user=user,articles=articles,avatar_url=avatar_url)

UPLOAD_FOLDER = 'app/static/uploads/avatars'  
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@auth_bp.route('/profile/edit', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        bio = request.form.get('bio')

        avatar = request.files.get('avatar')
        if avatar and allowed_file(avatar.filename):
            filename = secure_filename(avatar.filename)
            avatar_path = os.path.join(UPLOAD_FOLDER, filename)
            avatar.save(avatar_path)
            user.avatar_url = f'/uploads/avatars/{filename}'  
            session['avatar_url'] = user.avatar_url

        if bio:
            if len(bio) > 100:
                error_message = "Bio is too long! It should be up to 100 characters."
                return render_template('auth/edit_profile.html', error_message=error_message,user=user)
            user.bio = bio

        db.session.commit()
        return redirect(url_for('auth.user_profile', username=user.username))

    return render_template('auth/edit_profile.html', user=user)

@auth_bp.route('/profile/reset_avatar', methods=['POST'])
def reset_avatar():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    user = User.query.get(session['user_id'])

    user.avatar_url = 'img/default_avatar.jpg'  

    session['avatar_url'] = user.avatar_url
    db.session.commit()

    return redirect(url_for('auth.edit_profile'))
