document.addEventListener('DOMContentLoaded', function () {
    const socket = io();

    const room = document.getElementById('messages').dataset.room;
    const sender = document.getElementById('messages').dataset.sender;
    const recipientId = document.getElementById('messages').dataset.recipient;

    const messagesContainer = document.getElementById('messages');
    const messageInput = document.getElementById('message-input');

    function scrollToBottom() {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    setTimeout(scrollToBottom, 100);

    if (performance.getEntriesByType('navigation')[0].type === 'reload') {
        window.location.href = '/dialog';
        return;
    }

    socket.on('connect', function () {
        socket.emit('join_room', { room: room, recipient_id: recipientId });
    });

    socket.on('receive_message', function (data) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('message-item');
        
        if (String(data.sender) === String(sender)) {
            messageElement.classList.add('sent');
            messageElement.innerHTML = `
                <strong>You:</strong> ${data.content} 
                 ${data.photo_url ? `<div class="message-photo"><img src="${data.photo_url}" class="photo" /></div>` : ''}
                <span class="message-time" style="right: 0; bottom: 0; position: absolute;">${data.timestamp}</span>
                <span class="read-status">${data.read ? 'Read' : ''}</span>
            `;
        } else {
            messageElement.classList.add('received');
            messageElement.innerHTML = `
                <strong>${data.sender_username}:</strong> ${data.content}
                 ${data.photo_url ? `<div class="message-photo"><img src="${data.photo_url}" class="photo" /></div>` : ''}
                <span class="message-time" style="right: 0; bottom: 0; position: absolute;">${data.timestamp}</span>
            `;
    
            socket.emit('mark_as_read', {
                message_id: data.id,
                sender_id: data.sender,
            });
        }
    
        messagesContainer.appendChild(messageElement);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    });
    
    

    socket.on('update_message_status', function (data) {
        const userId = document.getElementById('messages').dataset.sender;
        if (data.status === 'read' && (String(data.sender_id) !== String(userId) || data.sender_id === '')) {
            const readElements = document.querySelectorAll('.read-status');
            readElements.forEach((el) => {
                el.textContent = 'Read';
            });
        }
    });

    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    document.getElementById('message-form').addEventListener('submit', function (event) {
        event.preventDefault();

        const content = messageInput.value.trim();
        if (content) {
            socket.emit('send_message', {
                room: room,
                sender: sender,
                recipient_id: recipientId,
                content: content
            });

            messageInput.value = '';
            messageInput.focus();
            setTimeout(scrollToBottom, 100);
        }
    });

    messageInput.addEventListener('keypress', function (event) {
        if (event.key === 'Enter') {
            event.preventDefault();
            document.getElementById('message-form').dispatchEvent(new Event('submit'));
        }
    });

    setTimeout(function () {
        messageInput.focus();
    }, 100);
    messageInput.addEventListener('input', function () {
        if (messageInput.value.trim() !== '') {
            socket.emit('typing', { room: room });
        }
    });
    
    let typingTimeout; 

    socket.on('user_typing', function (data) {
        console.log(data.sender_id, sender); 
    
        const typingIndicatorContainer = document.getElementById('typing-indicator-container');
        const existingTypingIndicator = document.getElementById('typing-indicator');
    
        if (String(data.sender_id) !== String(sender)) { 

            if (!existingTypingIndicator) {
                const typingElement = document.createElement('div');
                typingElement.id = 'typing-indicator';
                typingElement.textContent = `${data.sender_username} is typing...`;
                typingIndicatorContainer.appendChild(typingElement);
            }
    
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
            if (typingTimeout) {
                clearTimeout(typingTimeout);
            }
    
            typingTimeout = setTimeout(() => {
                const typingElement = document.getElementById('typing-indicator');
                if (typingElement) {
                    typingElement.remove();
                }   
                typingTimeout = null; 
            }, 2000);
        }
    });
document.getElementById('emoji-button').addEventListener('click', function () {
    const emojiMenu = document.getElementById('emoji-menu');
    const photoMenu = document.getElementById('photo-menu');
    
    emojiMenu.style.display = emojiMenu.style.display === 'none' || emojiMenu.style.display === '' ? 'block' : 'none';
    photoMenu.style.display = 'none'; 
});

document.querySelectorAll('.emoji').forEach(function (button) {
    button.addEventListener('click', function () {
        const emoji = button.textContent;
        messageInput.value += emoji;
        messageInput.focus() 
    });
});

document.getElementById('close-emoji-menu').addEventListener('click', function () {
    document.getElementById('emoji-menu').style.display = 'none';  
    messageInput.focus()
});

document.getElementById('photo-button').addEventListener('click', function () {
    const photoMenu = document.getElementById('photo-menu');
    const emojiMenu = document.getElementById('emoji-menu');
    
    photoMenu.style.display = photoMenu.style.display === 'none' || photoMenu.style.display === '' ? 'block' : 'none';
    emojiMenu.style.display = 'none';  
});

document.getElementById('send-photo').addEventListener('click', function () {
    const photoInput = document.getElementById('photo-upload');
    const file = photoInput.files[0];

    if (file) {
        const reader = new FileReader();
        reader.onload = function (e) {
            const photoDataUrl = e.target.result;  

            socket.emit('send_message', {
                room: room,
                sender: sender,
                recipient_id: recipientId,
                content: '',  
                photo: photoDataUrl,
            });
            document.getElementById('photo-menu').style.display = 'none';
            photoInput.value = '';  
            document.getElementById('file-name').textContent = 'No file selected'; 
        };
        reader.readAsDataURL(file);
    } else {
        alert('Please select an image to send.');
    }
});
document.getElementById('photo-upload').addEventListener('change', function() {
    const fileName = this.files[0] ? this.files[0].name : 'No file selected';
    document.getElementById('file-name').textContent = fileName;
});
document.getElementById('close-photo-menu').addEventListener('click', function() {
    document.getElementById('photo-menu').style.display = 'none';
});
messageInput.addEventListener('paste', function (event) {
    const clipboardItems = event.clipboardData.items;

    for (let i = 0; i < clipboardItems.length; i++) {
        const item = clipboardItems[i];
        
        if (item.type.startsWith('image/')) {
            const file = item.getAsFile();
            const reader = new FileReader();

            reader.onload = function (e) {
                const photoDataUrl = e.target.result;

                socket.emit('send_message', {
                    room: room,
                    sender: sender,
                    recipient_id: recipientId,
                    content: '', 
                    photo: photoDataUrl,
                });
                setTimeout(scrollToBottom, 100); 
            };

            reader.readAsDataURL(file);
            break; 
        }
    }
});
document.addEventListener('dragenter', (event) => {
    event.preventDefault();
    document.body.classList.add('dragging');
});

document.addEventListener('dragover', (event) => {
    event.preventDefault();
});

document.addEventListener('dragleave', (event) => {
    if (event.target === document || event.target === document.body) {
        document.body.classList.remove('dragging');
    }
});

document.addEventListener('drop', (event) => {
    event.preventDefault();
    document.body.classList.remove('dragging'); 

    const files = event.dataTransfer.files;

    if (files.length > 0) {
        const file = files[0];

        if (file.type.startsWith('image/')) {
            const reader = new FileReader();

            reader.onload = function (e) {
                const photoDataUrl = e.target.result;

                socket.emit('send_message', {
                    room: room,
                    sender: sender,
                    recipient_id: recipientId,
                    content: '', 
                    photo: photoDataUrl,
                });

                setTimeout(scrollToBottom, 100);
            };

            reader.readAsDataURL(file);
        } else {
            alert('Please drop an image file!');
        }
    }
});

});
