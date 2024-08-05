import os
from flask import Flask, request, render_template, redirect, url_for, send_file, session
from werkzeug.utils import secure_filename
import shutil
import sqlite3
import uuid

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

# Define input and output folders
input_folder = 'input'
output_folder = 'output'

# Ensure the input and output directories exist
os.makedirs(input_folder, exist_ok=True)
os.makedirs(output_folder, exist_ok=True)

# Database setup
def init_db():
    with sqlite3.connect('database.db') as conn:
        conn.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            tokens INTEGER DEFAULT 0
        )
        ''')
        conn.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        ''')

init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload/video', methods=['GET', 'POST'])
def upload_video():
    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            return redirect(request.url)
        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(input_folder, filename)
            file.save(filepath)
            # Run your video script here
            os.system(f'python3 Video_AI_Keyworder.py')
            # Assuming the script generates a CSV file in the output folder
            output_file = os.path.join(output_folder, 'results.csv')
            return send_file(output_file, as_attachment=True)
    return render_template('video.html')

@app.route('/upload/image', methods=['GET', 'POST'])
def upload_image():
    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            return redirect(request.url)
        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(input_folder, filename)
            file.save(filepath)
            # Run your image script here
            os.system(f'python3 Image_AI_Keyworder.py')
            # Assuming the script processes images and saves them in the output folder
            output_file = os.path.join(output_folder, filename)
            return send_file(output_file, as_attachment=True)
    return render_template('image.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        tokens = 10  # Initial tokens given to user
        with sqlite3.connect('database.db') as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users (email, tokens) VALUES (?, ?)', (email, tokens))
            conn.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        with sqlite3.connect('database.db') as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, tokens FROM users WHERE email = ?', (email,))
            user = cursor.fetchone()
            if user:
                session['user_id'] = user[0]
                session['tokens'] = user[1]
                return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    session.pop('tokens', None)
    return redirect(url_for('index'))

@app.route('/buy_tokens', methods=['POST'])
def buy_tokens():
    amount = int(request.form['amount'])
    if 'user_id' in session:
        with sqlite3.connect('database.db') as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET tokens = tokens + ? WHERE id = ?', (amount, session['user_id']))
            cursor.execute('INSERT INTO transactions (user_id, amount) VALUES (?, ?)', (session['user_id'], amount))
            conn.commit()
            session['tokens'] += amount
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
