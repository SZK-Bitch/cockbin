from functools import wraps
from flask import Flask, render_template, request, redirect, session, url_for, send_file, flash
import os
import uuid
import random
import hashlib
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'nUzZHI)%Wza8rPlRv^KMUBcYG#G@Q22p^ZtHbzfkdj9gb#'

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Define the path to the iplogs.txt file
comments_dict = {}


# Function to load comments from 'comments.txt'
def load_comments():
    try:
        with open('comments.txt', 'r') as file:
            lines = file.readlines()
            for line in lines:
                parts = line.strip().split('|')
                if len(parts) == 4:
                    unique_id, timestamp, username, text = parts
                    comment = {
                        'text': text,
                        'timestamp': timestamp,
                        'username': username
                    }
                    comments = comments_dict.get(unique_id, [])
                    comments.append(comment)
                    comments_dict[unique_id] = comments
                else:
                    print(f"Skipping invalid line: {line}")
    except FileNotFoundError:
        pass


# Load announcements and comments when the application starts
load_comments()


def generate_unique_url(filename):
    unique_id = str(uuid.uuid4())[:8]
    return f'/dox/{unique_id}/{filename}'


def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


def is_logged_in():
    return 'username' in session


def login_required(f):

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)

    return decorated_function


def is_owner(username):
    with open('owners.txt', 'r') as file:
        owners = file.read().splitlines()
    return username in owners


def can_delete(username):
    with open('owners.txt', 'r') as file:
        owners = file.read().splitlines()
    return username in owners


@app.route('/')
def landing():
    return render_template('landing.html')


@app.route('/credits')
def credits():
    return render_template('credits.html')


@app.route('/dox', methods=['GET', 'POST'])
@login_required
def dox():
    if request.method == 'POST':
        if 'file' in request.files:
            file = request.files['file']

            if file.filename != '':
                if not file.filename.endswith('.txt'):
                    flash("Invalid file format. Only .txt files are allowed.", 'error')
                    return redirect(request.url)

                dox_name = request.form.get('name')
                filename = f"{dox_name}.txt" if dox_name else f"dox.txt"

                if os.path.exists(os.path.join(UPLOAD_FOLDER, filename)):
                    flash("Name is already in use!", 'error')
                    return redirect(request.url)

                file.save(os.path.join(UPLOAD_FOLDER, filename))
                file_url = generate_unique_url(filename)

                return render_template('success.html', file_url=file_url)

        typed_text = request.form.get('text')
        if typed_text:
            dox_name = request.form.get('name')
            filename = f"{dox_name}.txt" if dox_name else f"dox.txt"

            if os.path.exists(os.path.join(UPLOAD_FOLDER, filename)):
                flash("Name is already in use!", 'error')
                return redirect(request.url)

            with open(os.path.join(UPLOAD_FOLDER, filename), 'w') as text_file:
                text_file.write(typed_text)

            file_url = generate_unique_url(filename)

            return render_template('success.html', file_url=file_url)

    doxes = os.listdir(UPLOAD_FOLDER)
    username = session.get('username')

    return render_template('dox.html',
                           username=username,
                           doxes=doxes,
                           is_owner=is_owner(username),
                           can_delete=can_delete(username))


@app.route('/dox/<unique_id>/<filename>')
def serve_dox(unique_id, filename):
    dox_path = os.path.join(UPLOAD_FOLDER, filename)

    if os.path.exists(dox_path):
        with open(dox_path, 'r') as dox_file:
            dox_content = dox_file.read()
    else:
        dox_content = "Dox not found."

    comments = comments_dict.get(unique_id, [])

    return render_template('dox_viewer.html',
                           dox_content=dox_content,
                           comments=comments,
                           unique_id=unique_id,
                           filename=filename)


@app.route('/dox/<unique_id>/<filename>/comments', methods=['GET', 'POST'])
def view_comments(unique_id, filename):
    if request.method == 'POST':
        comment_text = request.form.get('comment_text')
        if comment_text:
            comments = comments_dict.get(unique_id, [])
            comment = {
                'text': comment_text,
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'username': session.get('username')
            }
            comments.append(comment)
            comments_dict[unique_id] = comments
            save_comments_to_file()

    dox_url = generate_unique_url(filename)
    comments = comments_dict.get(unique_id, [])

    return render_template('comments.html',
                           dox_url=dox_url,
                           comments=comments,
                           unique_id=unique_id,
                           filename=filename)


def save_comments_to_file():
    with open('comments.txt', 'w') as file:
        for unique_id, comments in comments_dict.items():
            for comment in comments:
                file.write(
                    f"{unique_id}|{comment['timestamp']}|{comment['username']}|{comment['text']}\n"
                )


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        with open('users.txt', 'r') as file:
            lines = file.readlines()

        for line in lines:
            stored_username, stored_password = line.strip().split(':')
            if username == stored_username and hash_password(password) == stored_password:
                session['username'] = username
                return redirect('/dox')

        flash("Invalid username or password", 'error')

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect('/login')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        with open('users.txt', 'r') as file:
            lines = file.readlines()
            usernames = [line.strip().split(':')[0] for line in lines]

        if username in usernames:
            flash("Username already taken. Please choose another.", 'error')
            return redirect(request.url)

        if password != confirm_password:
            flash("Password and confirmation password do not match.", 'error')
            return redirect(request.url)

        hashed_password = hash_password(password)
        with open('users.txt', 'a') as file:
            file.write(f'{username}:{hashed_password}\n')

        return redirect('/login')

    return render_template('register.html')


@app.route('/hoa')
def hoa():
    return render_template('hoa.html')


@app.route('/delete_dox/<string:filename>')
@login_required
def delete_dox(filename):
    if can_delete(session.get('username')):
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.exists(file_path):
            os.remove(file_path)
    return redirect('/dox')


@app.route('/play_song')
def play_song():
    song_file_path = 'static/song.mp3'

    if os.path.exists(song_file_path):
        return send_file(song_file_path, as_attachment=True)

    return 'Song not found', 404


@app.route('/dox/<unique_id>/<filename>/edit', methods=['GET', 'POST'])
@login_required
def edit_dox(unique_id, filename):
    if not is_owner(session.get('username')):
        return redirect('/error')  # Redirect to an error page or main page

    if request.method == 'POST':
        edited_text = request.form.get('edited_text')
        if edited_text:
            with open(os.path.join(UPLOAD_FOLDER, filename), 'w') as text_file:
                text_file.write(edited_text)

            return redirect(url_for('serve_dox', unique_id=unique_id, filename=filename))

    dox_path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(dox_path):
        with open(dox_path, 'r') as dox_file:
            dox_content = dox_file.read()
    else:
        dox_content = "Dox not found."

    return render_template('dox_editer.html', dox_content=dox_content)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
