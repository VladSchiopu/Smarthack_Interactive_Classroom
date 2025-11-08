from flask import Flask
from flask_login import LoginManager
from .database import load_user

login_manager = LoginManager()
login_manager.login_view = "main.login"

def create_app():
    app = Flask(__name__)
    app.secret_key = "secret123"  # schimbă cu ceva sigur

    login_manager.init_app(app)

    from .routes import bp
    app.register_blueprint(bp)

    @login_manager.user_loader
    def user_loader(email):
        return load_user(email)

    return app
