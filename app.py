import os
from flask import Flask, request, render_template, redirect, url_for, send_file, session, flash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

# Configuration
app.config['UPLOAD_FOLDER'] = 'input'
app.config['OUTPUT_FOLDER'] = 'output'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

# Ensure the input and output directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload/image', methods=['GET', 'POST'])
def upload_image():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            # Run your image script here
            os.system(f'python3 Image_AI_Keyworder.py')
            # Assuming the script processes images and saves them in the output folder
            output_file = os.path.join(app.config['OUTPUT_FOLDER'], filename)
            if os.path.exists(output_file):
                return send_file(output_file, as_attachment=True)
            else:
                flash('Processed file not found')
                return redirect(request.url)
    return render_template('image.html')

@app.route('/upload/video', methods=['GET', 'POST'])
def upload_video():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            # Run your video script here
            os.system(f'python3 Video_AI_Keyworder.py')
            # Assuming the script generates a CSV file in the output folder
            output_file = os.path.join(app.config['OUTPUT_FOLDER'], 'results.csv')
            if os.path.exists(output_file):
                return send_file(output_file, as_attachment=True)
            else:
                flash('Processed file not found')
                return redirect(request.url)
    return render_template('video.html')

if __name__ == '__main__':
    app.run(debug=True)
