from flask import Blueprint, render_template, request, redirect, url_for, session
from werkzeug.utils import secure_filename
import os
from ..models import User, db, Article, LoginAttempt, AvatarChangeHistory, Message
import re
from .. import socketio
from flask_socketio import emit
import uuid
from datetime import datetime, timedelta

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
            return render_template('auth/create.html', error_message=error_message, username=username, email='')
        
        if len(password) < 8 or len(password) > 20:
            error_message = 'Password must be between 8 and 20 characters.'
            return render_template('auth/create.html', error_message=error_message, username=username, email='')
        
        if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
            error_message = 'Username or email already exists.'
            return render_template('auth/create.html', error_message=error_message, username='', email='')

        if password != confirm_password:
            error_message = 'Passwords do not match.'
            return render_template('auth/create.html', error_message=error_message,username=username, email=email)

        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        session['user_id'] = user.id
        session['username'] = user.username
        session['avatar_url'] = user.avatar_url
        return redirect(url_for('main.index'))

    return render_template('auth/create.html',username='', email='')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user_ip = request.remote_addr
        user_agent = request.headers.get('User-Agent')

        login_attempt = LoginAttempt.query.filter_by(
            ip_address=user_ip, user_agent=user_agent
        ).first()

        if login_attempt and login_attempt.is_locked_out():
            error_message = "Too many failed attempts. Try again later."
            return render_template('auth/login.html', error_message=error_message)

        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['avatar_url'] = user.avatar_url

            if login_attempt:
                db.session.delete(login_attempt)
                db.session.commit()
            
            return redirect(url_for('main.index'))
        
        if not login_attempt:
            login_attempt = LoginAttempt(
                ip_address=user_ip,
                user_agent=user_agent,
                failed_attempts=1,
                lockout_time=None
            )
            db.session.add(login_attempt)
        else:
            login_attempt.failed_attempts += 1
            if login_attempt.failed_attempts >= 5:
                login_attempt.lockout_time = datetime.utcnow() + timedelta(hours=1)
        
        db.session.commit()
        
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

    page = request.args.get('page', 1, type=int)
    query = request.args.get('query', '')

    articles_query = Article.query.filter_by(author_id=user.id)
    if query:
        articles_query = articles_query.filter(Article.title.ilike(f"%{query}%"))

    articles = articles_query.order_by(Article.date_posted.desc()).paginate(page=page, per_page=10)

    avatar_url = user.avatar_url
    return render_template(
        'auth/profile.html',
        user=user,
        articles=articles,
        avatar_url=avatar_url,query=query
    )


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
    history = AvatarChangeHistory.query.filter_by(user_id=user.id).first()
    if not history:
        history = AvatarChangeHistory(user_id=user.id, avatar_change_count=0, last_avatar_change=None)
        db.session.add(history)
        db.session.commit()

    if request.method == 'POST':
        bio = request.form.get('bio')
        avatar = request.files.get('avatar')

        if avatar and allowed_file(avatar.filename):
            now = datetime.utcnow()
            if history.last_avatar_change and now - history.last_avatar_change < timedelta(hours=1):
                if history.avatar_change_count >= 5:
                    error_message = "You can't change your avatar more than 5 times in an hour. Try again later."
                    return render_template('auth/edit_profile.html', error_message=error_message, user=user)

            unique_filename = f"{uuid.uuid4().hex}_{secure_filename(avatar.filename)}"
            avatar_path = os.path.join(UPLOAD_FOLDER, unique_filename)
            avatar.save(avatar_path)

            user.avatar_url = f'/uploads/avatars/{unique_filename}'
            session['avatar_url'] = user.avatar_url

            history.avatar_change_count += 1
            history.last_avatar_change = now
            db.session.commit()

        if bio:
            if len(bio) > 100:
                error_message = "Bio is too long! It should be up to 100 characters."
                return render_template('auth/edit_profile.html', error_message=error_message, user=user)
            user.bio = bio
            db.session.commit()

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

    return redirect(url_for('auth.user_profile', username=user.username))

@socketio.on('user_connected_to_site')
def handle_user_connected_to_site():
    user_id = session.get('user_id')
    if user_id:
        user = User.query.get(user_id)
        if user:
            user.is_online = True
            db.session.commit()

        unread_count_all = Message.query.filter_by(
            recipient_id=user_id,
            read=False
        ).count()

        emit('status_update', {'user_id': user_id, 'status': 'online'}, broadcast=True)
        emit('update_unread_count', {
    'unread_count_all': unread_count_all,
    'recipient_id': str(user_id)
}, broadcast=True)
