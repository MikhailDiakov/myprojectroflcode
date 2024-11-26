document.querySelectorAll('.btn-like, .btn-dislike').forEach(button => {
    button.addEventListener('click', function (event) {
        event.preventDefault();

        const action = this.value;
        const articleId = this.dataset.articleId;
        const url = `/articles/like/${articleId}`;

        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ action })
        })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert(data.error);
                } else {
                    document.querySelector('#likes-count').textContent = data.likes;
                    document.querySelector('#dislikes-count').textContent = data.dislikes;
                }
            })
            .catch(error => console.error('Error:', error));
    });
});

document.querySelector('#post-comment-btn').addEventListener('click', function (event) {
    event.preventDefault();
    postComment();
});

document.querySelector('#comment-input').addEventListener('keydown', function (event) {
    if (event.key === 'Enter') {
        event.preventDefault();
        postComment();
    }
});

function postComment() {
    const commentInput = document.querySelector('#comment-input');
    const content = commentInput.value.trim();
    const articleId = document.querySelector('#post-comment-btn').dataset.articleId;
    const url = `/articles/${articleId}/comment`;

    if (!content) {
        alert('Comment cannot be empty.');
        return;
    }

    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ content })
    })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                alert(data.error);
            } else {
                const commentList = document.querySelector('#comments-list');
                const newComment = document.createElement('li');

                let deleteButtonHtml = '';
                if (data.is_deletable) {
                    deleteButtonHtml = `
                        <button type="button" class="btn btn-primary delete-comment-btn"
                            data-comment-id="${data.comment_id}" style="width: 85px; height: 25px; font-size: 12px;">
                            Delete (1h)
                        </button>`;
                }

                newComment.setAttribute('id', `comment-${data.comment_id}`);
                newComment.innerHTML = `
                    <strong>${data.username}</strong>: ${data.content}
                    <span class="comment-date">(${data.date_posted})</span>
                    ${deleteButtonHtml}
                `;

                commentList.appendChild(newComment);

                commentInput.value = '';
                commentInput.focus();
            }
        })
        .catch(error => console.error('Error:', error));
}

document.querySelector('#comments-list').addEventListener('click', function (event) {
    if (event.target.matches('.delete-comment-btn')) {
        event.preventDefault();

        const commentId = event.target.dataset.commentId;
        const url = `/articles/comment/delete/${commentId}`;

        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert(data.error);
                } else {
                    const commentElement = document.querySelector(`#comment-${commentId}`);
                    if (commentElement) {
                        commentElement.remove();
                    }
                }
            })
            .catch(error => console.error('Error:', error));
    }
});
