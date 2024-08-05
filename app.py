import os
from flask import Flask, request, render_template, redirect, url_for, send_file, session, flash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Load environment variables from the specified path
load_dotenv('/etc/secrets/.env')  # Ensure this matches the path where your secrets are stored

# Initialize the Flask application
app = Flask(__name__)

# Load the secret key from the environment variable
secret_key = os.getenv("SECRET_KEY")
if not secret_key:
    raise ValueError("Secret key not found. Please set the SECRET_KEY environment variable.")

app.secret_key = secret_key

# Define the upload folder
UPLOAD_FOLDER = 'input'
OUTPUT_FOLDER = 'output'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

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
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # if user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)
