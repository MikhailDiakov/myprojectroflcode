from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
from datetime import datetime
from ..models import Article, db, Like, Comment

article_bp = Blueprint('articles', __name__, url_prefix='/articles')

@article_bp.route('/articles')
def articles():
    if 'user_id' not in session:  
        return render_template('articles/articles.html', message="You need to be logged in to view or post articles")

    query = request.args.get('query', '')  
    page = request.args.get('page', 1, type=int)

    articles_query = Article.query
    if query:
        articles_query = articles_query.filter(Article.title.ilike(f"%{query}%"))

    articles = articles_query.order_by(Article.date_posted.desc()).paginate(page=page, per_page=10)

    return render_template(
        'articles/articles.html',
        articles=articles,
        query=query  
    )

@article_bp.route('/<int:article_id>')
def article_detail(article_id):
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    else:
        article = Article.query.get_or_404(article_id)
        likes_count = Like.query.filter_by(article_id=article.id, is_like=1).count()
        dislikes_count = Like.query.filter_by(article_id=article.id, is_like=0).count() 
        current_time = datetime.utcnow()

        comments = Comment.query.filter_by(article_id=article.id).order_by(Comment.date_posted.asc()).all()

        return render_template('articles/article_detail.html', 
                               article=article,
                               likes_count=likes_count, 
                               dislikes_count=dislikes_count, 
                               current_time=current_time,
                               comments=comments)


@article_bp.route('/create', methods=['GET', 'POST'])
def create_article():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        if len(title) > 100:
            error_message = "Title is too long! It should be up to 100 characters."
            return render_template('articles/create_articles.html', error_message=error_message)

        new_article = Article(title=title, content=content, author_id=session['user_id'])
        db.session.add(new_article)
        db.session.commit()

        return redirect(url_for('articles.articles'))

    return render_template('articles/create_articles.html')

@article_bp.route('/edit/<int:article_id>', methods=['GET', 'POST'])
def edit_article(article_id):
    article = Article.query.get_or_404(article_id)

    if article.author_id != session.get('user_id'):
        return redirect(url_for('articles.articles'))

    if request.method == 'POST':
        article.title = request.form['title']
        article.content = request.form['content']
        article.date_modified = datetime.utcnow()
        db.session.commit()
        return redirect(url_for('articles.article_detail', article_id=article.id))

    return render_template('articles/edit_article.html', article=article)

@article_bp.route('/delete/<int:article_id>', methods=['POST'])
def delete_article(article_id):
    article = Article.query.get_or_404(article_id)

    if article.author_id != session.get('user_id'):
        return redirect(url_for('articles.articles'))

    Like.query.filter_by(article_id=article.id).delete()

    db.session.delete(article)
    db.session.commit()
    return redirect(url_for('articles.articles'))

@article_bp.route('/like/<int:article_id>', methods=['POST'])
def like_article_ajax(article_id):
    if 'user_id' not in session:
        return jsonify({'error': 'You must be logged in'}), 401

    action = request.json.get('action') 
    user_id = session['user_id']

    is_like = True if action == 'like' else False

    existing_like = Like.query.filter_by(user_id=user_id, article_id=article_id).first()

    if existing_like:
        existing_like.is_like = is_like
    else:
        new_like = Like(user_id=user_id, article_id=article_id, is_like=is_like)
        db.session.add(new_like)

    db.session.commit()

    likes_count = Like.query.filter_by(article_id=article_id, is_like=1).count()
    dislikes_count = Like.query.filter_by(article_id=article_id, is_like=0).count()
    print(likes_count, dislikes_count)

    return jsonify({'likes': likes_count, 'dislikes': dislikes_count})

import html

@article_bp.route('/<int:article_id>/comment', methods=['POST'])
def add_comment_ajax(article_id):
    if 'user_id' not in session:
        return jsonify({'error': 'You must be logged in'}), 401

    content = request.json.get('content')
    if not content or len(content) > 100:
        return jsonify({'error': 'Comment must be between 1 and 100 characters'}), 400

    content = html.escape(content)

    new_comment = Comment(content=content, user_id=session['user_id'], article_id=article_id)
    db.session.add(new_comment)
    db.session.commit()

    is_deletable = True 
    
    return jsonify({
        'username': new_comment.user.username,
        'content': new_comment.content,
        'date_posted': new_comment.date_posted.strftime('%b %d, %Y at %H:%M'),
        'is_deletable': is_deletable,
        'comment_id': new_comment.id
    })

@article_bp.route('/comment/delete/<int:comment_id>', methods=['POST'])
def delete_comment(comment_id):
    if 'user_id' not in session:
        return jsonify({'error': 'You must be logged in'}), 401

    comment = Comment.query.get_or_404(comment_id)

    if comment.user_id != session.get('user_id'):
        return jsonify({'error': 'You do not have permission to delete this comment'}), 403

    if (datetime.utcnow() - comment.date_posted).total_seconds() > 3600:
        return jsonify({'error': 'Comment deletion time has expired'}), 403

    db.session.delete(comment)
    db.session.commit()

    return jsonify({'success': True})
