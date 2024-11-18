from flask import Flask
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def create_app():
    app = Flask(__name__, instance_relative_config=True)
    
    app.config.from_object('instance.config.Config')

    db.init_app(app)

    from .routes.main import main_bp
    from .routes.auth import auth_bp
    from .routes.articles import article_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(article_bp)

    return app