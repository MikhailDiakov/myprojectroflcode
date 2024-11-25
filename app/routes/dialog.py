from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from ..models import User, Message, db
from datetime import datetime
from sqlalchemy import or_, desc

dialog_bp = Blueprint('dialog', __name__, url_prefix='/dialog')

def is_logged_in():
    return 'user_id' in session  

@dialog_bp.route('/')
def dialogs():
    if not is_logged_in():
        return redirect(url_for('auth.login'))  

    sender_id = session['user_id']
    users = db.session.query(User).join(Message, (Message.sender_id == User.id) | (Message.recipient_id == User.id)) \
                                .filter((Message.sender_id == sender_id) | (Message.recipient_id == sender_id)) \
                                .filter(User.id != sender_id).distinct() \
                                .all()

    last_messages = {}
    for user in users:
        last_message = Message.query.filter(
            (Message.sender_id == user.id) | (Message.recipient_id == user.id)
        ).order_by(Message.timestamp.desc()).first()

        if last_message:
            last_messages[user.id] = {
                'content': last_message.content,  
                'sender': last_message.sender,    
                'timestamp': last_message.timestamp  
            }
        

    return render_template('dialog/dialogs.html', users=users, last_messages=last_messages)

@dialog_bp.route('/<username>')
def dialog(username):
    if not is_logged_in():
        return redirect(url_for('auth.login'))  

    sender_id = session['user_id']
    recipient = User.query.filter_by(username=username).first_or_404() 
    messages = Message.query.filter(
        (Message.sender_id == sender_id) & (Message.recipient_id == recipient.id) |
        (Message.sender_id == recipient.id) & (Message.recipient_id == sender_id)
    ).order_by(Message.timestamp).all()

    return render_template('dialog/dialog.html', recipient=recipient, messages=messages)


@dialog_bp.route('/<username>/send', methods=['POST'])
def send_message(username):
    if not is_logged_in():
        return redirect(url_for('auth.login'))    

    sender_id = session['user_id']
    recipient = User.query.filter_by(username=username).first_or_404()  
    content = request.form.get('content', '').strip()

    if content:
        message = Message(sender_id=sender_id, recipient_id=recipient.id, content=content, timestamp=datetime.utcnow())
        db.session.add(message)
        db.session.commit()
        flash('Message sent!', 'success')
    else:
        flash('Message content cannot be empty.', 'error')

    return redirect(url_for('dialog.dialog', username=username))  

@dialog_bp.route('/<username>/update', methods=['GET'])
def update_messages(username):
    if not is_logged_in():
        return redirect(url_for('auth.login'))  

    sender_id = session['user_id']
    recipient = User.query.filter_by(username=username).first_or_404() 

    messages = Message.query.filter(
        (Message.sender_id == sender_id) & (Message.recipient_id == recipient.id) |
        (Message.sender_id == recipient.id) & (Message.recipient_id == sender_id)
    ).order_by(Message.timestamp).all()

    return render_template('dialog/messages.html', messages=messages, recipient=recipient)
