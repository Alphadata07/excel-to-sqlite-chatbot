# auth.py

USER_CREDENTIALS = {
    "admin": {"password": "admin123", "role": "admin"},
    "viewer": {"password": "viewer123", "role": "viewer"}
}

def authenticate(username, password):
    """Check if username/password are correct. Return role if valid, None if invalid."""
    user = USER_CREDENTIALS.get(username)
    if user and user["password"] == password:
        return user["role"]
    return None
