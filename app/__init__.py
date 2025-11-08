from flask import Flask
from flask_login import LoginManager
# from .users_db import load_user
from flask_sqlalchemy import SQLAlchemy

login_manager = LoginManager()
login_manager.login_view = "main.login"
db = SQLAlchemy()  # instanța bazei de date

def create_app():
    app = Flask(__name__)
    app.secret_key = "secret123"  # schimbă cu ceva sigur
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    login_manager.init_app(app)

    from .routes import bp
    app.register_blueprint(bp)

    from .models import User  # import modelul User

    @login_manager.user_loader
    def user_loader(user_id):
        try:
            return User.query.get(int(user_id))
        except ValueError:
            return None
    
    with app.app_context():
        db.create_all()

    return app
