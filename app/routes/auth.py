from flask import Blueprint, render_template, request, redirect, url_for, session, make_response, flash
from werkzeug.utils import secure_filename
import os
from ..models import User, db, Article, LoginAttempt, AvatarChangeHistory, Message, BlockedUser
import re
from .. import socketio
from flask_socketio import emit
import uuid
from datetime import datetime, timedelta
import hashlib
from itsdangerous import URLSafeTimedSerializer
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from instance.config import Config

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

            token = hashlib.sha256(f"{user.id}{user.username}".encode()).hexdigest()

            if login_attempt:
                db.session.delete(login_attempt)
                db.session.commit()

            resp = make_response(redirect(url_for('main.index')))
            resp.set_cookie('auth_token', token, max_age=60*60*24*30, httponly=True, secure=True)
            
            return resp
        
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

def send_reset_email(to_email, reset_link):
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    smtp_username = Config.smtp_username
    smtp_password = Config.smtp_password

    subject = "Password Reset Request"
    body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <h2 style="color: #4CAF50;">Password Reset Request</h2>
                <p>Hi,</p>
                <p>We received a request to reset your password. Please click the button below to reset it:</p>
                <p>
                    <a href="{reset_link}" 
                    style="display: inline-block; padding: 10px 20px; background-color: #4CAF50; color: #fff; text-decoration: none; border-radius: 5px;">
                    Reset Password
                    </a>
                </p>
                <p><strong>Note:</strong> This link is valid for <strong>1 hour</strong>. If you did not request this, you can safely ignore this email.</p>
                <p>Thank you!</p>
                <hr style="border: none; border-top: 1px solid #ddd;">
                <footer style="font-size: 0.9em; color: #666;">
                    <p>If you have any questions, please contact our support team.</p>
                </footer>
            </body>
        </html>
    """


    msg = MIMEMultipart()
    msg['From'] = smtp_username
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.send_message(msg)
        server.quit()
        print("Reset email sent successfully.")
    except Exception as e:
        print(f"Failed to send email: {e}")

def generate_reset_token(user_id):
    serializer = URLSafeTimedSerializer(Config.SECRET_KEY)
    return serializer.dumps(user_id, salt=Config.salt)

def confirm_reset_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(Config.SECRET_KEY)
    try:
        user_id = serializer.loads(token, salt=Config.salt, max_age=expiration)
    except Exception:
        return None
    return user_id

@auth_bp.route('/forget-password', methods=['GET', 'POST'])
def forget_password():
    if request.method == 'POST':
        email = request.form['email']
        user = User.query.filter_by(email=email).first()

        if user:
            reset_token = generate_reset_token(user.id)
            reset_link = url_for('auth.reset_password', token=reset_token, _external=True)

            send_reset_email(email, reset_link)

            success_message = 'Check your email for instructions to reset your password.'
            return render_template('auth/forget_password.html', success_message=success_message)
        else:
            error_message = 'Invalid email. Please check and try again.'
            return render_template('auth/forget_password.html', error_message=error_message)

    return render_template('auth/forget_password.html')

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    user_id = confirm_reset_token(token)
    if not user_id:
        error_message = "The reset link is invalid or has expired."
        return render_template('auth/reset_password.html', error_message=error_message)

    if request.method == 'POST':
        new_password = request.form['password']
        confirm_password = request.form['confirm_password']

        if len(new_password) < 8 or len(new_password) > 20:
            error_message = "Password must be between 8 and 20 characters."
            return render_template('auth/reset_password.html', error_message=error_message)

        if new_password != confirm_password:
            error_message = "Passwords do not match."
            return render_template('auth/reset_password.html', error_message=error_message)

        user = User.query.get(user_id)
        if user:
            user.set_password(new_password)
            db.session.commit()
            success_message = "Your password has been reset successfully. You can now log in."
            return render_template('auth/reset_password.html', success_message=success_message)

    return render_template('auth/reset_password.html')

@auth_bp.before_app_request
def auto_login():
    if 'user_id' not in session:
        token = request.cookies.get('auth_token')
        if token:
            user = verify_token(token)
            if user:
                session['user_id'] = user.id
                session['username'] = user.username
                session['avatar_url'] = user.avatar_url


def verify_token(token):
    for user in User.query.all():
        expected_token = hashlib.sha256(f"{user.id}{user.username}".encode()).hexdigest()
        if token == expected_token:
            return user
    return None

@auth_bp.route('/logout')
def logout():
    session.clear()
    resp = make_response(redirect(url_for('main.index')))
    resp.delete_cookie('auth_token')
    return resp

@auth_bp.route('/block_user/<username>', methods=['POST'])
def block_user(username):
    user_id = session.get('user_id')
    user_to_block = User.query.filter_by(username=username).first_or_404()

    existing_block = BlockedUser.query.filter_by(blocker_id=user_id, blocked_id=user_to_block.id).first()
    
    if not existing_block:
        new_block = BlockedUser(blocker_id=user_id, blocked_id=user_to_block.id)
        db.session.add(new_block)
        db.session.commit()
        flash(f'User {username} has been blocked.', 'success')
    else:
        flash(f'User {username} is already blocked.', 'info')

    return redirect(url_for('auth.user_profile', username=username))

@auth_bp.route('/unblock_user/<username>', methods=['POST'])
def unblock_user(username):
    user_id = session.get('user_id')
    user_to_unblock = User.query.filter_by(username=username).first_or_404()

    block_entry = BlockedUser.query.filter_by(blocker_id=user_id, blocked_id=user_to_unblock.id).first()

    if block_entry:
        db.session.delete(block_entry)
        db.session.commit()
        flash(f'User {username} has been unblocked.', 'success')
    else:
        flash(f'User {username} is not in your block list.', 'info')

    if request.referrer and 'blocked_users' in request.referrer:
        return redirect(url_for('auth.blocked_users'))

    return redirect(url_for('auth.user_profile', username=username))


@auth_bp.route('/change_email', methods=['POST'])
def change_email():
    new_email = request.form.get('new_email')
    old_password = request.form.get('old_password')
    user_id = session.get('user_id')

    if not user_id:
        return redirect(url_for('auth.login'))

    user = User.query.get(user_id)
    if not user:
        return redirect(url_for('auth.login'))
    
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    if not re.match(email_regex, new_email):
        error_message = 'Invalid email address format.'
        return render_template('auth/edit_profile.html', error_message=error_message, user=user)
    
    if len(new_email) > 255:
        error_message = 'Email address is too long.'
        return render_template('auth/edit_profile.html', error_message=error_message, user=user)

    if not user.check_password(old_password):
        error_message = "Incorrect password."
        return render_template('auth/edit_profile.html', error_message=error_message, user=user)

    if User.query.filter_by(email=new_email).first():
        error_message = "This email is already in use."
        return render_template('auth/profile.html', error_message=error_message, user=user)

    user.email = new_email
    db.session.commit()
    session['username'] = user.username
    success_message = "Email changed successfully."
    return render_template('auth/edit_profile.html', error_message=success_message, user=user)

@auth_bp.route('/change_password', methods=['POST'])
def change_password():
    current_password = request.form.get('current_password')
    new_password = request.form.get('new_password')
    confirm_new_password = request.form.get('confirm_new_password')
    user_id = session.get('user_id')

    if not user_id:
        return redirect(url_for('auth.login'))

    user = User.query.get(user_id)
    if not user:
        return redirect(url_for('auth.login'))

    if not user.check_password(current_password):
        error_message = "Incorrect current password."
        return render_template('auth/edit_profile.html', error_message=error_message, user=user)
    
    if len(new_password) < 8 or len(new_password) > 20:
        error_message = 'Password must be between 8 and 20 characters.'
        return render_template('auth/edit_profile.html', error_message=error_message, user=user)

    if new_password != confirm_new_password:
        error_message = "Passwords do not match."
        return render_template('auth/edit_profile.html', error_message=error_message, user=user)

    user.set_password(new_password)
    db.session.commit()
    success_message = "Password changed successfully."
    return render_template('auth/edit_profile.html', error_message=success_message, user=user)


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

    blocked_user_exists = BlockedUser.query.filter_by(blocker_id=session.get('user_id'), blocked_id=user.id).first() is not None

    avatar_url = user.avatar_url
    return render_template(
        'auth/profile.html',
        user=user,
        articles=articles,
        avatar_url=avatar_url,query=query, blocked_user_exists=blocked_user_exists
    )

@auth_bp.route('/blocked_users', methods=['GET'])
def blocked_users():
    user_id = session.get('user_id')
    
    if not user_id:
        flash('You must be logged in to view this page.', 'danger')
        return redirect(url_for('auth.login'))

    blocked_users = BlockedUser.query.filter_by(blocker_id=user_id).all()
    
    blocked_by_users = BlockedUser.query.filter_by(blocked_id=user_id).all()
    
    return render_template('auth/blocked_users.html', blocked_users=blocked_users, blocked_by_users=blocked_by_users)

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

        if bio is not None:
            if len(bio) > 100:
                error_message = "Bio is too long! It should be up to 100 characters."
                return render_template('auth/edit_profile.html', error_message=error_message, user=user)

            user.bio = bio if bio else ''
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