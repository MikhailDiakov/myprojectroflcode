from flask import Blueprint, render_template

main_bp = Blueprint('main', __name__,template_folder='templates')

@main_bp.route('/')
@main_bp.route('/index')
def index():
    return render_template('index.html')

@main_bp.route('/about')
def about():
    return render_template('about.html')
