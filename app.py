import os
from flask import Flask, request, render_template, redirect, url_for, send_file, flash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Retrieve environment variables
openai_api_key = os.getenv("OPENAI_API_KEY")
secret_key = os.getenv("SECRET_KEY")

# Debug: Print to verify loading environment variables
print("Loaded OPENAI_API_KEY:", openai_api_key)
print("Loaded SECRET_KEY:", secret_key)

# Initialize the Flask application
app = Flask(__name__)

if not secret_key:
    raise ValueError("Secret key not found. Please set the SECRET_KEY environment variable.")

app.secret_key = secret_key

# Define the upload folder
UPLOAD_FOLDER = 'input'
OUTPUT_FOLDER = 'output'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'mp4', 'mov', 'avi'}

# Ensure the input and output directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['OUTPUT_FOLDER'] = OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
        if file and allowed_file(file.filename) and file.filename.lower().endswith(('png', 'jpg', 'jpeg')):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            # Process the file here or call your processing script
            os.system(f'python3 Image_AI_Keyworder.py')
            output_file = os.path.join(app.config['OUTPUT_FOLDER'], filename)
            # Make sure the output_file exists before sending
            if os.path.exists(output_file):
                return send_file(output_file, as_attachment=True)
            else:
                flash('File processing failed.')
                return redirect(request.url)
    return render_template('upload_image.html')

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
        if file and allowed_file(file.filename) and file.filename.lower().endswith(('mp4', 'mov', 'avi')):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            # Process the file here or call your processing script
            os.system(f'python3 Video_AI_Keyworder.py')
            output_file = os.path.join(app.config['OUTPUT_FOLDER'], filename)
            # Make sure the output_file exists before sending
            if os.path.exists(output_file):
                return send_file(output_file, as_attachment=True)
            else:
                flash('File processing failed.')
                return redirect(request.url)
    return render_template('upload_video.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)
