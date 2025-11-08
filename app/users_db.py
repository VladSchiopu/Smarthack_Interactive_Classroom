from werkzeug.security import generate_password_hash

users = {}  # {"email": {"name": "...", "password": "..."}}

def add_user(email, name, password):
    users[email] = {
        "name": name,
        "password": generate_password_hash(password)
    }

def get_user(email):
    return users.get(email)

def load_user(email):
    user = get_user(email)
    if not user:
        return None
    from .routes import User
    return User(email, user["name"])
