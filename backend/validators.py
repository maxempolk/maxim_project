import re

def validate_username(username):
    return re.match(r"^[a-zA-Z][a-zA-Z0-9_-]*$", username) is not None

def validate_email(email):
    return re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email) is not None

def validate_password(password):
    return re.match(r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[!@#$%^&*])[A-Za-z\d!@#$%^&*]{8,}$", password) is not None

