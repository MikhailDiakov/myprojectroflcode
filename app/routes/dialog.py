from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from flask_socketio import join_room, emit, leave_room
from ..models import User, Message, db, Reaction, BlockedUser
from datetime import datetime
from .. import socketio
from collections import defaultdict
import base64
from io import BytesIO
from PIL import Image
import os
from werkzeug.utils import secure_filename
from instance.config import Config
from html import escape

user_last_activity = {}

dialog_bp = Blueprint('dialog', __name__, url_prefix='/dialog')
active_users = defaultdict(set)

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
            ((Message.sender_id == user.id) & (Message.recipient_id == sender_id)) | 
            ((Message.sender_id == sender_id) & (Message.recipient_id == user.id))
        ).order_by(Message.timestamp.desc()).first()

        if last_message:
            unread_count = Message.query.filter(
                (Message.sender_id == user.id) & 
                (Message.recipient_id == sender_id) & 
                (Message.read == False)
            ).count()
            
            last_messages[user.id] = {
                'content': last_message.content,
                'sender': last_message.sender,
                'timestamp': last_message.timestamp,
                'unread_count': unread_count,
                'sender_id': user.id,
                'is_online': user.is_online 
            }

    sorted_users = sorted(users, key=lambda u: last_messages[u.id]['timestamp'] if u.id in last_messages else 0, reverse=True)

    return render_template('dialog/dialogs.html', users=sorted_users, last_messages=last_messages)


def get_reaction_symbol(reaction_type):
    reaction_dict = {
    'like': '👍',
    'dislike': '👎',
    'heart': '❤️',
    'smile': '😊',  
    'sad': '😢',
    }
    return reaction_dict.get(reaction_type, '')

@dialog_bp.route('/<username>')
def dialog(username):
    if not is_logged_in():
        return redirect(url_for('auth.login')) 

    sender_id = session['user_id']
    recipient = User.query.filter_by(username=username).first_or_404() 

    room = f"chat_{min(sender_id, recipient.id)}_{max(sender_id, recipient.id)}"

    messages = Message.query.filter(
        ((Message.sender_id == sender_id) & (Message.recipient_id == recipient.id)) |
        ((Message.sender_id == recipient.id) & (Message.recipient_id == sender_id)),
        Message.reactions == False
    ).order_by(Message.timestamp).all()

    reactions = Reaction.query.filter(Reaction.message_id.in_([msg.id for msg in messages])).all()

    return render_template('dialog/dialog.html', recipient=recipient, messages=messages, room=room, reactions=reactions, get_reaction_symbol=get_reaction_symbol,api_key=Config.LINKPREVIEW_API_KEY)

@socketio.on('join_room')
def handle_join_room(data):
    user_id = session.get('user_id')
    room = data.get('room')
    recipient_id = data.get('recipient_id')

    if user_id and room:
        active_users[user_id].add(request.sid)
        join_room(room)

        block_check_sender = BlockedUser.query.filter_by(blocker_id=recipient_id, blocked_id=user_id).first()
        block_check_recipient = BlockedUser.query.filter_by(blocker_id=user_id, blocked_id=recipient_id).first()

        if block_check_sender:
            emit('block_notification', {'message': 'You are blocked by this user'}, room=room)
            return

        if block_check_recipient:
            emit('block_notification', {'message': 'You have blocked this user'}, room=room)
            return

        if recipient_id:
            Message.query.filter_by(sender_id=recipient_id, recipient_id=user_id, read=False) \
                .update({'read': True})

            reactions_to_delete = Message.query.filter_by(
                sender_id=recipient_id,
                recipient_id=user_id,
                reactions=True
            ).all()

            for reaction in reactions_to_delete:
                db.session.delete(reaction)

            db.session.commit()

            emit('update_message_status', {
                'status': 'read',
                'sender_id': user_id
            }, room=room)


@socketio.on('disconnect')
def handle_disconnect():
    user_id = session.get('user_id')
    if user_id:
        user = User.query.get(user_id)
        if user:
            user.is_online = False
            db.session.commit()

        emit('status_update', {'user_id': user_id, 'status': 'offline'}, broadcast=True)
        active_users[user_id].discard(request.sid)
        if not active_users[user_id]:
            del active_users[user_id]


@socketio.on('send_message')
def handle_send_message(data):
    room = data['room']
    content = data['content']
    sender_id = session.get('user_id')
    recipient_id = data.get('recipient_id')

    photo_data = data.get('photo')  
    photo_url = None

    if photo_data:
        img_data = base64.b64decode(photo_data.split(',')[1]) 
        image = Image.open(BytesIO(img_data))
        
        filename = f'{secure_filename(str(sender_id))}_{datetime.utcnow().strftime("%Y%m%d%H%M%S")}.png'
        file_path = os.path.join('app/static/uploads/photos', filename)
        image.save(file_path)
        
        photo_url = f'/static/uploads/photos/{filename}' 
        content = ' '

    if sender_id and recipient_id:
        message = Message(
            sender_id=sender_id,
            recipient_id=recipient_id,
            content=content,
            photo_url=photo_url,
            timestamp=datetime.utcnow(),
            read=False
        )
        db.session.add(message)
        db.session.commit()

        sender_username = User.query.get(sender_id).username
        recipient_username = User.query.get(recipient_id).username
        avatar_url = User.query.get(sender_id).avatar_url

        unread_count = Message.query.filter_by(
            recipient_id=recipient_id,
            sender_id=sender_id,
            read=False
        ).count()

        emit('receive_message', {
            'id': message.id, 
            'sender': sender_id,
            'sender_username': sender_username,
            'recipient_username': recipient_username,
            'content': content,
            'photo_url': photo_url,  
            'timestamp': message.timestamp.strftime('%H:%M %d/%m'),
            'read': False
        }, room=room)

        emit('update_last_message', {
            'sender_id': sender_id,
            'sender_username': sender_username,
            'avatar': avatar_url,
            'recipient_id': recipient_id,
            'content': content,
            'photo_url': photo_url, 
            'timestamp': message.timestamp.strftime('%H:%M %d/%m'),
            'unread_count': unread_count
        }, broadcast=True)

        unread_count_all = Message.query.filter_by(
            recipient_id=recipient_id,
            read=False
        ).count()
        emit('update_unread_count', {'unread_count_all': unread_count_all, 'recipient_id': recipient_id}, broadcast=True)

@socketio.on('delete_message')
def handle_delete_message(data):
    message_id = data.get('message_id')
    user_id = session.get('user_id')
    
    message = Message.query.get(message_id)
    
    if message and message.sender_id == user_id:
        message.content = "DELETED MESSAGE"
        message.deleted = True
        message.photo_url = None
        db.session.commit()

        room = f"chat_{min(message.sender_id, message.recipient_id)}_{max(message.sender_id, message.recipient_id)}"
        
        emit('update_message', {
            'id': message_id,
            'content': "DELETED",
            'deleted': True,
            'photo_url': None
        }, room=room)


@socketio.on('edit_message')
def handle_edit_message(data):
    message_id = data.get('message_id')
    new_content = data.get('content')
    user_id = session.get('user_id')

    message = Message.query.get(message_id)

    if message and message.sender_id == user_id:
        message.content = new_content
        message.edited = True
        db.session.commit()

        escaped_content = escape(new_content)

        room = f"chat_{min(message.sender_id, message.recipient_id)}_{max(message.sender_id, message.recipient_id)}"
        
        emit('update_message', {
            'id': message_id,
            'content': escaped_content,
            'edited': True
        }, room=room)

@socketio.on('mark_as_read')
def handle_mark_as_read(data):
    user_id = session.get('user_id')
    message_id = data.get('message_id')
    sender_id = data.get('sender_id')
    reaction_author = data.get('reaction_author')

    if user_id and message_id and sender_id:
        message = Message.query.filter_by(id=message_id, recipient_id=user_id, sender_id=sender_id, read=False).first()
        
        
        if message:
            message.read = True
            db.session.commit()
            
            
            emit('update_message_status', {
                'message_id': message.id, 
                'status': 'read',
                'recipient_id': '',
                'sender_id': '',
            }, room=f"chat_{min(sender_id, user_id)}_{max(sender_id, user_id)}")

    else:
        message_reactions = Message.query.filter_by(
            recipient_id=reaction_author, 
            sender_id=sender_id, 
            read=False, 
            reactions=True
        ).all()

        if message_reactions:
            for reaction in message_reactions:
                db.session.delete(reaction)
            db.session.commit()



@socketio.on('typing')
def handle_typing(data):
    room = data['room']
    sender_id = session.get('user_id')
    if sender_id and room:
        sender_username = User.query.get(sender_id).username
        emit('user_typing', {
            'sender_id': sender_id,
            'sender_username': sender_username
        }, room=room)

@socketio.on('send_reaction')
def handle_reaction(data):
    reaction = Reaction.query.filter_by(
        message_id=data['message_id'],
        user_id=data['sender']
    ).first()

    if reaction:
        reaction.reaction_type = data['reaction_type']
    else:

        reaction = Reaction(
            message_id=data['message_id'],
            reaction_type=data['reaction_type'],
            user_id=data['sender']
        )
        db.session.add(reaction)

    db.session.commit()

    socketio.emit('receive_reaction', {
        'sender': session.get('user_id'),
        'message_id': data['message_id'],
        'reaction_type': data['reaction_type']
    }, room=data['room'])

    sender_id = session.get('user_id')
    recipient_id = data.get('recipient_id')

    if sender_id and recipient_id:
        message = Message(
            sender_id=sender_id,
            recipient_id=recipient_id,
            content='Reactions',
            reactions = True,
            timestamp=datetime.utcnow(),
            read=False
        )
        db.session.add(message)
        db.session.commit()

        sender_username = User.query.get(sender_id).username
        avatar_url = User.query.get(sender_id).avatar_url

    unread_count = Message.query.filter_by(
            recipient_id=recipient_id,
            sender_id=sender_id,
            read=False
        ).count()

    emit('update_last_message', {
            'sender_id': sender_id,
            'sender_username': sender_username,
            'avatar': avatar_url,
            'recipient_id': recipient_id,
            'content': 'Reactions',
            'reactions': True,
            'timestamp': message.timestamp.strftime('%H:%M %d/%m'),
            'unread_count': unread_count
        }, broadcast=True)

@socketio.on('remove_reaction')
def handle_remove_reaction(data):
    reaction = Reaction.query.filter_by(
        message_id=data['message_id'],
        user_id=data['sender']
    ).first()

    if reaction:
        db.session.delete(reaction)
        db.session.commit()

    socketio.emit('remove_reaction', {
        'message_id': data['message_id']
    }, room=data['room'])

