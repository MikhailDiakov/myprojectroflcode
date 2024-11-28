document.addEventListener('DOMContentLoaded', function () {
    const socket = io();

    const room = document.getElementById('messages').dataset.room;
    const sender = document.getElementById('messages').dataset.sender;
    const recipientId = document.getElementById('messages').dataset.recipient;

    const messagesContainer = document.getElementById('messages');
    const messageInput = document.getElementById('message-input');

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
                <span class="message-time" style="right: 0; bottom: 0; position: absolute;">${data.timestamp}</span>
                <span class="read-status">${data.read ? 'Read' : ''}</span>
            `;
        } else {
            messageElement.classList.add('received');
            messageElement.innerHTML = `
                <strong>${data.sender_username}:</strong> ${data.content} 
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
});
