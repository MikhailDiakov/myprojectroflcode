document.addEventListener('DOMContentLoaded', function () {
    const socket = io();

    const room = document.getElementById('messages').dataset.room;
    const sender = document.getElementById('messages').dataset.sender;
    const recipientId = document.getElementById('messages').dataset.recipient;

    const messagesContainer = document.getElementById('messages');
    const messageInput = document.getElementById('message-input');

    socket.on('connect', function () {
        socket.emit('join_room', { room: room });
    });

    socket.on('receive_message', function (data) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('message-item');
        if (String(data.sender) === String(sender)) {
            messageElement.classList.add('sent');
            messageElement.innerHTML = `<strong>You:</strong> ${data.content} <span class="message-time" style="right: 0; bottom: 0; position: absolute;">${data.timestamp}</span>`;
        } else {
            messageElement.classList.add('received');
            messageElement.innerHTML = `<strong>${data.sender_username}:</strong> ${data.content} <span class="message-time" style="right: 0; bottom: 0; position: absolute;">${data.timestamp}</span>`;
        }


        messagesContainer.appendChild(messageElement);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
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
