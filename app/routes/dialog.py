from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_socketio import join_room, emit
from ..models import User, Message, db
from datetime import datetime
from .. import socketio

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

    room = f"chat_{min(sender_id, recipient.id)}_{max(sender_id, recipient.id)}"
    print('ROOM',room)

    messages = Message.query.filter(
        ((Message.sender_id == sender_id) & (Message.recipient_id == recipient.id)) |
        ((Message.sender_id == recipient.id) & (Message.recipient_id == sender_id))
    ).order_by(Message.timestamp).all()

    return render_template('dialog/dialog.html', recipient=recipient, messages=messages, room=room)

@socketio.on('join_room')
def handle_join_room(data):
    if not isinstance(data, dict): 
        print("Invalid data format:", data)
        return

    room = data.get('room')
    if room:
        join_room(room)
        print(f"User joined room {room}")
    else:
        print("Room not provided in data:", data)

@socketio.on('send_message')
def handle_send_message(data):
    room = data['room']
    content = data['content']
    sender_id = session.get('user_id')
    recipient_id = data.get('recipient_id')

    if sender_id and recipient_id and content:
        message = Message(sender_id=sender_id, recipient_id=recipient_id, content=content, timestamp=datetime.utcnow())
        db.session.add(message)
        db.session.commit()

        sender_username = User.query.get(sender_id).username
        recipient_username = User.query.get(recipient_id).username

        emit('receive_message', {
            'sender': sender_id,
            'sender_username': sender_username, 
            'recipient_username': recipient_username, 
            'content': content,
            'timestamp': message.timestamp.strftime(('%H:%M %d/%m'))
        }, room=room)
