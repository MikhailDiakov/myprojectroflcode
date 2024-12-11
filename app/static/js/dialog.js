document.addEventListener('DOMContentLoaded',async function () {
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

    const editButtons = document.querySelectorAll('.edit-message');
    const deleteButtons = document.querySelectorAll('.delete-message');

    deleteButtons.forEach(button => {
        button.addEventListener('click', function () {
        const messageElement = button.closest('.message-item');
        const messageTextElement = messageElement.querySelector('.message-text');
        const messagePhotoElement = messageElement.querySelector('.message-photo');
        const messageId = messageElement.dataset.id;

        if (confirm("Are you sure you want to delete this message?")) {
            if (messageTextElement) {
                messageTextElement.innerHTML = "MESSAGE DELETED";
            }
            if (messagePhotoElement) {
                messagePhotoElement.innerHTML = ""; 
            }

            messageElement.classList.add('deleted');

                const editButton = messageElement.querySelector('.edit-message');
                const deleteButton = messageElement.querySelector('.delete-message');
                editButton.style.display = 'none';
                deleteButton.style.display = 'none';

                socket.emit('delete_message', {
                    message_id: messageId
                });

            }
        });
    });

    editButtons.forEach(button => {
        button.addEventListener('click', function () {
            const messageElement = button.closest('.message-item');
            const messageTextElement = messageElement.querySelector('.message-text');
            const messageId = messageElement.dataset.id; 
            const currentText = messageTextElement.innerHTML;

            button.style.display = 'none';
            const deleteButton = messageElement.querySelector('.delete-message');
            deleteButton.style.display = 'none';

            messageTextElement.innerHTML = `<div contenteditable="true" class="edit-text" style="width: 100%; min-height: 50px;">${currentText}</div>`;
            const editableText = messageTextElement.querySelector('.edit-text');
            const editedLabel = messageElement.querySelector('.edited-label');
            if (editedLabel) {
                editedLabel.remove();
            }
            setTimeout(scrollToBottom, 100);
            setTimeout(() => {
                editableText.focus();
            }, 100);

            const saveButton = document.createElement('button');
            saveButton.innerText = 'Save';
            saveButton.classList.add('save-message');
            messageElement.appendChild(saveButton);

            saveButton.addEventListener('click', function () {
                const newContent = editableText.innerText.trim();

                if (newContent === "") {
                    alert("Message cannot be empty.");
                    editableText.focus();
                    return;
                }


                if (newContent !== currentText) {  
                    let editedLabel = messageTextElement.querySelector('.edited-label');
                    if (!editedLabel) {
                        editedLabel = document.createElement('span');
                        editedLabel.classList.add('edited-label');
                        editedLabel.style.color = 'gray';
                        editedLabel.style.marginLeft = '10px';
                        editedLabel.textContent = '(Edited)';
                        messageTextElement.appendChild(editedLabel);
                    }

                    socket.emit('edit_message', {
                        message_id: messageId,
                        content: newContent
                    });

                    messageTextElement.innerHTML = newContent;
                }

                saveButton.remove();
                button.style.display = 'inline';
                deleteButton.style.display = 'inline';
            });

            editableText.addEventListener('keydown', function (event) {
                if (event.key === 'Enter') {
                    event.preventDefault();
                    saveButton.click();
                }
            });
        });
    });
    
    async function processMessages() {
        const messageItems = messagesContainer.querySelectorAll('.message-item');
        for (const messageItem of messageItems) {
            const content = messageItem.querySelector('.message-content');
            if (content) {
                const updatedContent = await createClickableLinks(content.innerHTML);
                content.innerHTML = updatedContent;
            }
        }
    }
    
    
    async function createClickableLinks(text) {
        const urlRegex = /(https?:\/\/[^\s]+)/g;
        const matches = text.match(urlRegex);
    
        if (!matches) return text;
    
        let updatedText = text;
    
        for (const url of matches) {
            const linkPreviewHTML = await getLinkPreview(url);
            if (linkPreviewHTML) {
                updatedText = updatedText.replace(url, linkPreviewHTML);
            }
        }
    
        return updatedText;
    }
    
    function truncateText(text, maxLength) {
        if (text.length > maxLength) {
            return text.slice(0, maxLength) + '...';
        }
        return text;
    }
    
    const cache = JSON.parse(localStorage.getItem('linkPreviewCache')) || {};

    async function getLinkPreview(url) {
        if (cache[url]) {
            const sizeInBytes = new Blob([JSON.stringify(cache[url])]).size;
            return cache[url];
        }
    
        const apiUrl = `https://api.linkpreview.net/?key=${apiKey}&q=${encodeURIComponent(url)}`;
    
        try {
            const response = await fetch(apiUrl);
            if (!response.ok) throw new Error('Request failed');
            
            const data = await response.json();
    
            if (data.error || !data.title || !data.description || !data.image) {
                return `<a href="${url}" target="_blank" class="message-link">${url}</a>`;
            }
    
            const previewHTML = `
                <div class="link-preview">
                    <a href="${data.url}" target="_blank" class="link-preview-container">
                        <img src="${data.image}" alt="${data.title}" class="link-preview-image" />
                        <div class="link-preview-info">
                            <h4 class="link-preview-title">${data.title}</h4>
                            <p class="link-preview-description">${truncateText(data.description, 150)}</p>
                        </div>
                    </a>
                </div>
            `;
    
            cache[url] = previewHTML;
            localStorage.setItem('linkPreviewCache', JSON.stringify(cache));
    
            return previewHTML;
        } catch (error) {
            return `<a href="${url}" target="_blank" class="message-link">${url}</a>`;
        }
    }    
    
    
    const style = document.createElement('style');
    style.textContent = `
    .link-preview {
        display: flex;
        align-items: center;
        margin: 10px 0;
        border: 1px solid #ddd;
        border-radius: 8px;
        overflow: hidden;
        text-decoration: none;
        color: inherit;
        transition: box-shadow 0.3s ease;
    }
    .link-preview:hover {
        box-shadow: 0 4px 10px rgba(0, 0, 0, 0.2);
    }
    .link-preview-container {
        display: flex;
        text-decoration: none;
        color: inherit;
    }
    .link-preview-image {
        width: 100px;
        height: 100px;
        object-fit: cover;
    }
    .link-preview-info {
        padding: 10px;
    }
    .link-preview-title {
        margin: 0;
        font-size: 16px;
        font-weight: bold;
    }
    .link-preview-description {
        margin: 5px 0 0;
        font-size: 14px;
        color: #555;
    }
    `;
    document.head.appendChild(style);
    async function main() {
        await processMessages();
        setTimeout(scrollToBottom, 100);
      }

    main()

    socket.on('connect', function () {
        socket.emit('join_room', { room: room, recipient_id: recipientId });
    });

    socket.on('receive_message', async function (data) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('message-item');
        messageElement.setAttribute('data-id', data.id);
    
        messageElement.addEventListener('mousedown', function (event) {
            if (event.detail === 2) {
                event.preventDefault();
            }
        });
    
        const clickableContent = await createClickableLinks(data.content);
    
        const messageContent = `
            <span class="message-text">${clickableContent}</span>
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
    
        if (String(data.sender) === String(sender)) {
            messageElement.classList.add('sent');
            const isLink = /https?:\/\/[^\s]+/.test(data.content);

            messageElement.innerHTML = `
                <strong>You:</strong> ${messageContent}
                <span class="read-status">${data.read ? 'Read' : ''}</span>
                <button class="edit-message" data-message-id="${data.id}" style="display: ${isLink ? 'none' : 'inline'};">🖍️</button>
                <button class="delete-message" data-message-id="${data.id}">🗑️</button>
            `;
            
    
            const editButton = messageElement.querySelector('.edit-message');
            const deleteButton = messageElement.querySelector('.delete-message');
            const messageTextElement = messageElement.querySelector('.message-text');
    
            const saveMessage = function (newContent) {
                data.content = newContent;
                if (newContent === "") {
                    alert("Message cannot be empty.");
                    editableText.focus();
                    return;
                }
    
                messageTextElement.innerHTML = newContent;
                

            const messageWrapper = messageTextElement.parentNode;
            if (messageWrapper) {
                let editedLabel = messageWrapper.querySelector('.edited-label');
                if (!editedLabel) {
                    editedLabel = document.createElement('span');
                    editedLabel.classList.add('edited-label');
                    editedLabel.style.color = 'gray';
                    editedLabel.style.marginLeft = '10px';
                    editedLabel.textContent = '(Edited)';
                    messageWrapper.appendChild(editedLabel);
                } else {
                    console.log('Edited label already exists.');
                }
            } else {
                console.error('Parent node for message text not found!');
            }

                editButton.innerHTML = '🖍️';
                editButton.style.display = 'inline';
                deleteButton.style.display = 'inline';
    
                editButton.removeEventListener('click', saveHandler);
                editButton.addEventListener('click', editHandler);
    
                socket.emit('edit_message', {
                    message_id: data.id,
                    content: newContent
                });
            };
    
            const editHandler = function () {
                const currentText = messageTextElement.innerHTML;
    
                editButton.style.display = 'none';
                deleteButton.style.display = 'none';
    
                messageTextElement.innerHTML = `<div contenteditable="true" class="edit-text" style="width: 50%; height: 50px; overflow-y: auto;">${currentText}</div>`;
                const editableText = messageTextElement.querySelector('.edit-text');
                editableText.focus();
    
                editButton.innerHTML = 'Save';
                editButton.style.display = 'inline';
    
                editButton.removeEventListener('click', editHandler);
                editButton.addEventListener('click', saveHandler);
                

                setTimeout(scrollToBottom, 100);
                setTimeout(() => {
                    editableText.focus();
                }, 100);
    
                editableText.addEventListener('keydown', function (event) {
                    if (event.key === 'Enter') {
                        event.preventDefault();
                        saveMessage(editableText.textContent);
                    }
                });
            };
    
            const saveHandler = function () {
                const editableText = messageTextElement.querySelector('.edit-text');
                saveMessage(editableText.textContent);
            };
    
            editButton.addEventListener('click', editHandler);
    
            deleteButton.addEventListener('click', function () {
                if (confirm("Are you sure you want to delete this message?")) {
                    messageTextElement.innerHTML = "DELETED MESSAGE";
                    messageElement.classList.add('deleted');

                    const editedLabel = messageElement.querySelector('.edited-label');
                    if (editedLabel) {
                        editedLabel.remove();
                    }
    
                    editButton.style.display = 'none';
                    deleteButton.style.display = 'none';
    
                    socket.emit('delete_message', {
                        message_id: data.id
                    });
                }
            });
    
        } else {
            messageElement.classList.add('received');
            messageElement.innerHTML = `
                <strong>${data.sender_username}:</strong> ${messageContent}
            `;
    
            socket.emit('mark_as_read', {
                message_id: data.id,
                sender_id: data.sender,
            });
        }

        messagesContainer.appendChild(messageElement);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    
        const currentUserId = document.getElementById('messages').dataset.sender;
    
        messageElement.addEventListener('dblclick', function () {
            const reactionContainer = document.getElementById(`reaction-${data.id}`);
    
            if (String(data.sender) !== String(currentUserId)) {
                if (reactionContainer && reactionContainer.textContent.trim() !== '') {
                    removeReaction(data.id);
                } else {
                    toggleReactionMenu(data.id);
                }
            }
        });
    });
    socket.on('update_message', function (data) {
        const messageElement = document.querySelector(`[data-id="${data.id}"]`);
        
        if (data.deleted) {
            const messageTextElement = messageElement.querySelector('.message-text');
            messageTextElement.innerHTML = "DELETED MESSAGE";
            messageElement.classList.add('deleted');
            

            const messagePhotoElement = messageElement.querySelector('.message-photo');
            if (messagePhotoElement) {
                messagePhotoElement.remove();
            }
        }
        
        if (data.edited) {
            const messageTextElement = messageElement.querySelector('.message-text');
            messageTextElement.innerHTML = data.content;
        
            let editedLabel = messageElement.querySelector('.edited-label');
            if (!editedLabel) {
                editedLabel = document.createElement('span');
                editedLabel.classList.add('edited-label');
                editedLabel.style.color = 'gray';
                editedLabel.style.marginLeft = '10px';
                editedLabel.textContent = '(Edited)';
                messageTextElement.parentNode.appendChild(editedLabel); 
            } else {
                editedLabel.style.display = 'inline'; 
            }
        }
    
        if (data.photo_url) {
            const messagePhotoElement = messageElement.querySelector('.message-photo img');
            if (messagePhotoElement) {
                messagePhotoElement.src = data.photo_url;
            }
        }
    });
    
    
    
    
document.getElementById('messages').addEventListener('click', function (event) {
    if (event.target && event.target.classList.contains('reaction')) {
        const messageId = event.target.getAttribute('data-message-id');
        const reactionType = event.target.getAttribute('data-reaction');
        sendReaction(messageId, reactionType);
        document.getElementById(`reactions-${messageId}`).style.display = 'none';
    }

    if (event.target && event.target.classList.contains('close-reactions')) {
        const messageId = event.target.getAttribute('data-message-id');
        document.getElementById(`reactions-${messageId}`).style.display = 'none'; 
    }
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

    document.getElementById('message-form').addEventListener('submit', function (event) {
        event.preventDefault(); 
        handleFormSubmit();
    });
    
    messageInput.addEventListener('keypress', function (event) {
        if (event.key === 'Enter') {
            event.preventDefault();
            document.getElementById('message-form').requestSubmit(); 
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
function toggleReactionMenu(messageId) {
    const reactionMenu = document.getElementById(`reactions-${messageId}`);
    const allReactionMenus = document.querySelectorAll('.reactions');
    const messagesContainer = document.getElementById('messages');
    const messageElement = document.querySelector(`.message-item[data-id="${messageId}"]`);

    const currentUserId = document.getElementById('messages').dataset.sender;
    const authorId = messageElement.getAttribute('data-author-id'); 

    if (authorId === currentUserId) {
        return; 
    }

    allReactionMenus.forEach(function(menu) {
        if (menu !== reactionMenu) {
            menu.style.display = 'none';
        }
    });

    if (reactionMenu.style.display === 'none' || reactionMenu.style.display === '') {
        reactionMenu.style.display = 'block';
        
        const rect = reactionMenu.getBoundingClientRect();
        const containerRect = messagesContainer.getBoundingClientRect();

        if (rect.bottom > containerRect.bottom) {
            messagesContainer.scrollTop += rect.bottom - containerRect.bottom; 
        }

        if (rect.top < containerRect.top) {
            messagesContainer.scrollTop -= containerRect.top - rect.top; 
        }
    } else {
        reactionMenu.style.display = 'none';
    }
}

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

function removeReaction(messageId) {
    const room = document.getElementById('messages').dataset.room;
    const sender = document.getElementById('messages').dataset.sender;
    const recipientId = document.getElementById('messages').dataset.recipient;
    const currentUserId = document.getElementById('messages').dataset.sender;

    const messageElement = document.querySelector(`.message-item[data-id="${messageId}"]`);

    let authorId = null;
    if (messageElement) {
        authorId = messageElement.getAttribute('data-author-id');
    }
    if (authorId === currentUserId) {
        return; 
    }


    socket.emit('remove_reaction', {
        room: room,
        sender: sender,
        recipient_id: recipientId,
        message_id: messageId,
    });

    const reactionContainer = document.getElementById(`reaction-${messageId}`);
    reactionContainer.textContent = ''; 
}

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


document.querySelectorAll('.message-item').forEach(function (messageElement) {
    messageElement.addEventListener('mousedown', function (event) {
        if (event.detail === 2) {
            event.preventDefault();
        }
    });

    messageElement.addEventListener('dblclick', function () {
        const messageId = messageElement.getAttribute('data-id');
        const reactionContainer = document.getElementById(`reaction-${messageId}`);
        
        if (reactionContainer && reactionContainer.textContent.trim() !== '') {
            removeReaction(messageId);
        } else {
            toggleReactionMenu(messageId);
        }
    });
});


document.querySelectorAll('.close-reactions').forEach(function (button) {
    button.addEventListener('click', function () {
        const messageId = button.getAttribute('data-message-id');
        const reactionsMenu = document.getElementById(`reactions-${messageId}`);
        reactionsMenu.style.display = 'none'; 
    });
});
socket.on('receive_reaction', function (data) {
    const messageElement = document.querySelector(`.message-item[data-id="${data.message_id}"]`);
    if (messageElement) {
        const reactionContainer = messageElement.querySelector('.message-reaction');
        const sender = document.getElementById('messages').dataset.sender;
        reactionContainer.textContent = getReactionSymbol(data.reaction_type);

        const authorElement = messageElement.querySelector('.reaction-author');
        if (authorElement) {
            authorElement.textContent = `Reacted by: ${data.reaction_author}`;
        }

        const reactionAuthorId = messageElement.getAttribute('data-author-id');
        
        if (String(sender) !== String(data.sender)) {
            socket.emit('mark_as_read', {
                sender_id: data.sender,
                reaction_author: reactionAuthorId
            });
        }
    }
});

socket.on('remove_reaction', function (data) {

    const messageElement = document.querySelector(`.message-item[data-id="${data.message_id}"]`);
    
    if (messageElement) {
        const reactionContainer = messageElement.querySelector('.message-reaction');
        reactionContainer.textContent = '';
    }
});
});