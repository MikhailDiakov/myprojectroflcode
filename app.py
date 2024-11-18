from datetime import datetime
import re
from flask import request, redirect, url_for, session
from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config.from_pyfile('config.py')
app.secret_key = app.config['SECRET_KEY']
app.config['SQLALCHEMY_DATABASE_URI'] = app.config['DATABASE_URL']
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(21), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
class Article(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    author = db.relationship('User', backref=db.backref('articles', lazy=True))
    date_posted = db.Column(db.DateTime, default=datetime.utcnow)
    date_modified = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)  

    def __repr__(self):
        return f'<Article {self.title}>'


@app.route('/index')
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/articles')
def articles():
    if 'user_id' not in session:  
        return render_template('articles.html', message="You need to be logged in to view or post articles")

    articles = Article.query.order_by(Article.date_posted.desc()).all()
    return render_template('articles.html', articles=articles)

@app.route('/create', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        if len(username) < 3 or len(username) > 20:
            error_message = 'Username must be between 3 and 20 characters.'
            return render_template('create.html', error_message=error_message, username=username, email=email)
        
        email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        if not re.match(email_regex, email) or len(email) > 255:
            error_message = 'Invalid email address format.'
            return render_template('create.html', error_message=error_message, username=username, email=email)
        
        if len(password) < 8 or len(password) > 20:
            error_message = 'Password must be between 8 and 20 characters.'
            return render_template('create.html', error_message=error_message, username=username, email=email)
        
        if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
            error_message = 'Username or email already exists.'
            return render_template('create.html', error_message=error_message, username=username, email=email)
        if password != confirm_password:
            error_message = 'Passwords do not match. Please try again.'
            return render_template('create.html', error_message=error_message, username=username, email=email)
        
        
        user = User(username=username, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        session['user_id'] = user.id
        session['username'] = user.username
        
        return redirect(url_for('index'))  

    return render_template('create.html')

@app.route('/articles/create', methods=['GET', 'POST'])
def create_article():
    if 'user_id' not in session:
        return redirect(url_for('login'))  

    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        if len(title) > 100:
            error_message = "Title is too long! It should be up to 100 characters."
            return render_template('create_articles.html', error_message=error_message, title=title, content=content)
        
        new_article = Article(title=title, content=content, author_id=session['user_id'])
        db.session.add(new_article)
        db.session.commit()
        
        return redirect(url_for('articles'))

    return render_template('create_articles.html')

@app.route('/articles/<int:article_id>')
def article_detail(article_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    else:
        article = Article.query.get_or_404(article_id)
        return render_template('article_detail.html', article=article)

@app.route('/user/<username>')
def user_profile(username):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    else:
        user = User.query.filter_by(username=username).first_or_404()
        articles = Article.query.filter_by(author_id=user.id).order_by(Article.date_posted.desc()).all()
        return render_template('user_profile.html', user=user, articles=articles)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('index'))
        else:
            error_message = 'Invalid username or password. Please try again.'
            return render_template('login.html', error_message=error_message,username=username)

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('username', None)
    return redirect(url_for('index'))

@app.route('/articles/edit/<int:article_id>', methods=['GET', 'POST'])
def edit_article(article_id):
    article = Article.query.get_or_404(article_id)

    if article.author_id != session.get('user_id'):
        return redirect(url_for('articles'))  

    if request.method == 'POST':
        article.title = request.form['title']
        article.content = request.form['content']
        article.date_modified = datetime.utcnow()
        db.session.commit()  
        return redirect(url_for('article_detail', article_id=article.id))

    return render_template('edit_article.html', article=article)

@app.route('/articles/delete/<int:article_id>', methods=['POST'])
def delete_article(article_id):
    article = Article.query.get_or_404(article_id)
    
    if article.author_id != session.get('user_id'):
        return redirect(url_for('articles'))

    db.session.delete(article)
    db.session.commit()
    return redirect(url_for('articles'))

if __name__ == '__main__':
    app.run(debug=True)