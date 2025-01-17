import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO 

db = SQLAlchemy()
socketio = SocketIO() 

def create_app():
    app = Flask(__name__, instance_relative_config=True)

    instance_folder = 'instance'
    if not os.path.exists(instance_folder):
        os.makedirs(instance_folder)

    config_file = os.path.join(instance_folder, 'config.py')
    if not os.path.exists(config_file):
        with open(config_file, 'w') as f:
            f.write("""
import os
                    
class Config:
    SECRET_KEY = os.urandom(24)  #Replace with your secret key
    SQLALCHEMY_DATABASE_URI = 'sqlite:///iambored.db' 
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    LINKPREVIEW_API_KEY = '7c80729903a4c7a5b55dd4beb745f556'  #If you wanna change to your API key https://my.linkpreview.net/
    smtp_username = "invalid" #Put your e-mail in here
    smtp_password = "invalid" #Put your e-mail app-password in here
    salt = os.urandom(24) #You can also change the salt to reset the token.
            """)

    app.config.from_object('instance.config.Config')
    
    app.config.from_object('instance.config.Config')

    db.init_app(app)
    socketio.init_app(app)  

    upload_folders = ['app/static/uploads/avatars', 'app/static/uploads/photos','app/static/uploads/documents']

    for folder in upload_folders:
        if not os.path.exists(folder):
            os.makedirs(folder)

    from .routes.main import main_bp
    from .routes.auth import auth_bp
    from .routes.articles import article_bp
    from .routes.dialog import dialog_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(article_bp)
    app.register_blueprint(dialog_bp)

    return app
