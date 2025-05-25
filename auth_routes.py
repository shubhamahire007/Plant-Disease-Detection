# auth_routes.py — handles login, register, logout
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import json
import os

auth = Blueprint('auth', __name__)

USERS_FILE = 'users.json'

# Load users from file
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {}

# Save users to file
def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        users = load_users()
        user = users.get(email)
        if user and check_password_hash(user['password'], password):
            session['user'] = email
            # flash('Logged in successfully!', 'success')
            if email == 'admin@plantshield.com':
                return redirect('/admin')
            else:
                return redirect('/')
        else:
            print()
            # flash('Invalid credentials', 'danger')

    return render_template('login.html')

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        users = load_users()
        if email in users:
            # flash('Email already registered.', 'warning')
            return redirect('/register')

        users[email] = {
            'password': generate_password_hash(password),
            'history': []
        }
        save_users(users)
        # flash('Registration successful! Please login.', 'success')
        return redirect('/login')

    return render_template('register.html')

@auth.route('/logout')
def logout():
    session.pop('user', None)
    # flash('Logged out successfully.', 'info')

    return redirect('/')
