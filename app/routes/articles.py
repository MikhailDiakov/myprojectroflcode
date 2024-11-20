from flask import Blueprint, render_template, request, redirect, url_for, session
from datetime import datetime
from ..models import Article, db

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
        return render_template('articles/article_detail.html', article=article)

@article_bp.route('/create', methods=['GET', 'POST'])
def create_article():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        if len(title) > 100:
            error_message = "Title is too long! It should be up to 100 characters."
            return render_template('articles/create.html', error_message=error_message)

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

    db.session.delete(article)
    db.session.commit()
    return redirect(url_for('articles.articles'))