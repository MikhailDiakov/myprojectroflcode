document.addEventListener('DOMContentLoaded', function () {
    const socket = io();

    const currentUserId = document.body.dataset.sender; 

    const unreadCountElement = document.getElementById('unread-count');
    const cachedUnreadCount = localStorage.getItem('unreadCount');
    if (unreadCountElement && cachedUnreadCount !== null) {
        unreadCountElement.textContent = cachedUnreadCount; 
    }

    socket.on('update_unread_count', function (data) {
        if (data.recipient_id === currentUserId) {
            if (unreadCountElement) {
                unreadCountElement.textContent = data.unread_count_all;
                localStorage.setItem('unreadCount', data.unread_count_all);
            }
        }
    });
    socket.on('update_last_message', function (data) {
        if (data.recipient_id !== currentUserId) return;

        showToast(data);
    });
    
});

function showToast(data) {
    const toastContainer = document.getElementById('toast-container');

    const toast = document.createElement('div');
    toast.classList.add('toast-message');
    toast.textContent = `${data.sender_username}: ${data.content}`;

    toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('show');
    }, 100);

    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}
