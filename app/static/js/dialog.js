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

// Обработчик события для получения сообщения
socket.on('receive_message', function (data) {
    const messageElement = document.createElement('div');
    messageElement.classList.add('message-item');
    messageElement.setAttribute('data-id', data.id); // Устанавливаем id сообщения для обработки реакций

    // Оформляем сообщение в зависимости от того, отправил ли его текущий пользователь
    if (String(data.sender) === String(sender)) {
        messageElement.classList.add('sent');
        messageElement.innerHTML = `
            <strong>You:</strong> ${data.content} 
            ${data.photo_url ? `<div class="message-photo"><img src="${data.photo_url}" class="photo" /></div>` : ''}
            <span class="message-time" style="right: 0; bottom: 0; position: absolute;">${data.timestamp}</span>
            <span class="read-status">${data.read ? 'Read' : ''}</span>
            <span class="message-reaction" id="reaction-${data.id}">
                <!-- Реакция будет отображаться здесь -->
            </span>
            <div class="reactions" id="reactions-${data.id}" style="display: none;">
                <button class="reaction" data-message-id="${data.id}" data-reaction="like">👍</button>
                <button class="reaction" data-message-id="${data.id}" data-reaction="dislike">👎</button>
                <button class="reaction" data-message-id="${data.id}" data-reaction="heart">❤️</button>
                <button class="reaction" data-message-id="${data.id}" data-reaction="smile">😊</button>
                <button class="reaction" data-message-id="${data.id}" data-reaction="sad">😢</button>
                <button class="close-reactions" data-message-id="${data.id}">❌</button>
            </div>
        `;
    } else {
        messageElement.classList.add('received');
        messageElement.innerHTML = `
            <strong>${data.sender_username}:</strong> ${data.content}
            ${data.photo_url ? `<div class="message-photo"><img src="${data.photo_url}" class="photo" /></div>` : ''}
            <span class="message-time" style="right: 0; bottom: 0; position: absolute;">${data.timestamp}</span>
            <span class="message-reaction" id="reaction-${data.id}">
                <!-- Реакция будет отображаться здесь -->
            </span>
            <div class="reactions" id="reactions-${data.id}" style="display: none;">
                <button class="reaction" data-message-id="${data.id}" data-reaction="like">👍</button>
                <button class="reaction" data-message-id="${data.id}" data-reaction="dislike">👎</button>
                <button class="reaction" data-message-id="${data.id}" data-reaction="heart">❤️</button>
                <button class="reaction" data-message-id="${data.id}" data-reaction="smile">😊</button>
                <button class="reaction" data-message-id="${data.id}" data-reaction="sad">😢</button>
                <button class="close-reactions" data-message-id="${data.id}">❌</button>
            </div>
        `;
        
        socket.emit('mark_as_read', {
            message_id: data.id,
            sender_id: data.sender,
        });
    }

    // Добавляем новое сообщение в контейнер
    messagesContainer.appendChild(messageElement);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;

    // Делаем меню реакций доступным по двойному клику
    messageElement.addEventListener('dblclick', function () {
        const reactionContainer = document.getElementById(`reaction-${data.id}`);
        
        // Если реакция уже существует, удаляем ее, иначе открываем меню
        if (reactionContainer.textContent !== '') {
            removeReaction(data.id);
        } else {
            toggleReactionMenu(data.id);
        }
    });
});

// Делегирование событий для кнопок реакции и закрытия меню
document.getElementById('messages').addEventListener('click', function (event) {
    // Проверяем, кликнули ли по кнопке реакции
    if (event.target && event.target.classList.contains('reaction')) {
        const messageId = event.target.getAttribute('data-message-id');
        const reactionType = event.target.getAttribute('data-reaction');
        sendReaction(messageId, reactionType);
        document.getElementById(`reactions-${messageId}`).style.display = 'none'; // Скрыть меню после выбора реакции
    }

    // Проверяем, кликнули ли по кнопке закрытия меню реакций
    if (event.target && event.target.classList.contains('close-reactions')) {
        const messageId = event.target.getAttribute('data-message-id');
        document.getElementById(`reactions-${messageId}`).style.display = 'none'; // Закрыть меню
    }
});

// Функция для отображения или скрытия меню реакций
function toggleReactionMenu(messageId) {
    const reactionMenu = document.getElementById(`reactions-${messageId}`);
    const allReactionMenus = document.querySelectorAll('.reactions');

    // Закрыть все другие меню реакций
    allReactionMenus.forEach(function(menu) {
        if (menu !== reactionMenu) {
            menu.style.display = 'none';
        }
    });

    // Переключить видимость текущего меню
    if (reactionMenu.style.display === 'none' || reactionMenu.style.display === '') {
        reactionMenu.style.display = 'block';
    } else {
        reactionMenu.style.display = 'none';
    }
}

// Функция для отправки реакции
function sendReaction(messageId, reactionType) {
    socket.emit('send_reaction', {
        room: room,
        sender: sender,
        recipient_id: recipientId,
        message_id: messageId,
        reaction_type: reactionType,
    });

    const reactionContainer = document.getElementById(`reaction-${messageId}`);
    reactionContainer.textContent = getReactionSymbol(reactionType);
}

// Функция для удаления реакции
function removeReaction(messageId) {
    const room = document.getElementById('messages').dataset.room;
    const sender = document.getElementById('messages').dataset.sender;
    const recipientId = document.getElementById('messages').dataset.recipient;

    socket.emit('remove_reaction', {
        room: room,
        sender: sender,
        recipient_id: recipientId,
        message_id: messageId,
    });

    const reactionContainer = document.getElementById(`reaction-${messageId}`);
    reactionContainer.textContent = ''; // Удаляем реакцию
}

// Функция для получения смайлика реакции
function getReactionSymbol(reactionType) {
    switch (reactionType) {
        case 'like': return '👍';
        case 'dislike': return '👎';
        case 'heart': return '❤️';
        case 'smile': return '😊';
        case 'sad': return '😢';
        default: return '';
    }
}


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
// Функция для отображения или скрытия меню реакций
function toggleReactionMenu(messageId) {
    const reactionMenu = document.getElementById(`reactions-${messageId}`);
    const allReactionMenus = document.querySelectorAll('.reactions');
    const messagesContainer = document.getElementById('messages');
    const messageElement = document.querySelector(`.message-item[data-id="${messageId}"]`);

    const currentUserId = document.getElementById('messages').dataset.sender;
    const authorId = messageElement.getAttribute('data-author-id'); // Исправлена ошибка

    if (authorId === currentUserId) {
        return; // Прерываем выполнение
    }

    // Закрыть все другие меню реакций
    allReactionMenus.forEach(function(menu) {
        if (menu !== reactionMenu) {
            menu.style.display = 'none';
        }
    });

    // Переключить видимость текущего меню
    if (reactionMenu.style.display === 'none' || reactionMenu.style.display === '') {
        reactionMenu.style.display = 'block';
        
        // Проверяем, не выходит ли меню за пределы контейнера сообщений
        const rect = reactionMenu.getBoundingClientRect();
        const containerRect = messagesContainer.getBoundingClientRect();

        // Если меню выходит за пределы контейнера снизу
        if (rect.bottom > containerRect.bottom) {
            messagesContainer.scrollTop += rect.bottom - containerRect.bottom; // Прокручиваем вниз
        }

        // Если меню выходит за пределы контейнера сверху
        if (rect.top < containerRect.top) {
            messagesContainer.scrollTop -= containerRect.top - rect.top; // Прокручиваем вверх
        }
    } else {
        reactionMenu.style.display = 'none';
    }
}

// Функция для отправки реакции через сокет
function sendReaction(messageId, reactionType) {
    const room = document.getElementById('messages').dataset.room;
    const sender = document.getElementById('messages').dataset.sender;
    const recipientId = document.getElementById('messages').dataset.recipient;

    socket.emit('send_reaction', {
        room: room,
        sender: sender,
        recipient_id: recipientId,
        message_id: messageId,
        reaction_type: reactionType,
    });

    const reactionContainer = document.getElementById(`reaction-${messageId}`);
    reactionContainer.textContent = getReactionSymbol(reactionType);
}

// Функция для удаления реакции
function removeReaction(messageId) {
    const room = document.getElementById('messages').dataset.room;
    const sender = document.getElementById('messages').dataset.sender;
    const recipientId = document.getElementById('messages').dataset.recipient;

    socket.emit('remove_reaction', {
        room: room,
        sender: sender,
        recipient_id: recipientId,
        message_id: messageId,
    });

    const reactionContainer = document.getElementById(`reaction-${messageId}`);
    reactionContainer.textContent = ''; // Удаляем реакцию
}

// Функция для получения смайлика в зависимости от типа реакции
function getReactionSymbol(reactionType) {
    switch (reactionType) {
        case 'like': return '👍';
        case 'dislike': return '👎';
        case 'heart': return '❤️';
        case 'smile': return '😊';
        case 'sad': return '😢';
        default: return '';
    }
}


// Обработчик для двойного клика на сообщение
document.querySelectorAll('.message-item').forEach(function (messageElement) {
    messageElement.addEventListener('dblclick', function () {
        const messageId = messageElement.getAttribute('data-id');
        const reactionMenu = document.getElementById(`reactions-${messageId}`);

        if (reactionMenu.style.display === 'none' || reactionMenu.style.display === '') {
            toggleReactionMenu(messageId);
        } else {
            const reactionContainer = document.getElementById(`reaction-${messageId}`);
            if (reactionContainer.textContent !== '') {
                removeReaction(messageId);
            } else {
                toggleReactionMenu(messageId);
            }
        }
    });
});
document.querySelectorAll('.close-reactions').forEach(function (button) {
    button.addEventListener('click', function () {
        const messageId = button.getAttribute('data-message-id');
        const reactionsMenu = document.getElementById(`reactions-${messageId}`);
        reactionsMenu.style.display = 'none'; // Закрываем меню реакции
    });
});
// Слушатель для получения реакции с сервера
socket.on('receive_reaction', function (data) {
    const messageElement = document.querySelector(`.message-item[data-id="${data.message_id}"]`);
    
    if (messageElement) {
        const reactionContainer = messageElement.querySelector('.message-reaction');
        reactionContainer.textContent = getReactionSymbol(data.reaction_type);
    }
});

// Слушатель для удаления реакции с сервера
socket.on('remove_reaction', function (data) {

    const messageElement = document.querySelector(`.message-item[data-id="${data.message_id}"]`);
    
    if (messageElement) {
        const reactionContainer = messageElement.querySelector('.message-reaction');
        reactionContainer.textContent = '';
    }
});
});