import os
from flask import Flask, request, render_template, redirect, url_for, send_file, flash, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Load environment variables directly
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

# Initialize the database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
db = SQLAlchemy(app)

# Define the User model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Define the upload folders
UPLOAD_FOLDER_IMAGE = 'input_image'
OUTPUT_FOLDER_IMAGE = 'output_image'
UPLOAD_FOLDER_VIDEO = 'input_video'
OUTPUT_FOLDER_VIDEO = 'output_video'
ALLOWED_EXTENSIONS_IMAGE = {'png', 'jpg', 'jpeg'}
ALLOWED_EXTENSIONS_VIDEO = {'mp4', 'mov', 'avi'}

# Ensure the input and output directories exist
os.makedirs(UPLOAD_FOLDER_IMAGE, exist_ok=True)
os.makedirs(OUTPUT_FOLDER_IMAGE, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_VIDEO, exist_ok=True)
os.makedirs(OUTPUT_FOLDER_VIDEO, exist_ok=True)

app.config['UPLOAD_FOLDER_IMAGE'] = UPLOAD_FOLDER_IMAGE
app.config['OUTPUT_FOLDER_IMAGE'] = OUTPUT_FOLDER_IMAGE
app.config['UPLOAD_FOLDER_VIDEO'] = UPLOAD_FOLDER_VIDEO
app.config['OUTPUT_FOLDER_VIDEO'] = OUTPUT_FOLDER_VIDEO
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password, method='sha256')
        new_user = User(username=username, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        else:
            flash('Login unsuccessful. Check username and password.')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/upload/image', methods=['GET', 'POST'])
@login_required
def upload_image():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename, ALLOWED_EXTENSIONS_IMAGE):
            filename = secure_filename(file.filename)
            user_folder = os.path.join(app.config['UPLOAD_FOLDER_IMAGE'], str(current_user.id))
            os.makedirs(user_folder, exist_ok=True)
            filepath = os.path.join(user_folder, filename)
            file.save(filepath)
            # Process the file here or call your processing script
            os.system(f'python3 Image_AI_Keyworder.py')
            output_file = os.path.join(app.config['OUTPUT_FOLDER_IMAGE'], str(current_user.id), filename)
            # Make sure the output_file exists before sending
            if os.path.exists(output_file):
                return send_file(output_file, as_attachment=True)
            else:
                flash('File processing failed.')
                return redirect(request.url)
    return render_template('upload_image.html')

@app.route('/upload/video', methods=['GET', 'POST'])
@login_required
def upload_video():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename, ALLOWED_EXTENSIONS_VIDEO):
            filename = secure_filename(file.filename)
            user_folder = os.path.join(app.config['UPLOAD_FOLDER_VIDEO'], str(current_user.id))
            os.makedirs(user_folder, exist_ok=True)
            filepath = os.path.join(user_folder, filename)
            file.save(filepath)
            # Process the file here or call your processing script
            os.system(f'python3 Video_AI_Keyworder.py')
            output_file = os.path.join(app.config['OUTPUT_FOLDER_VIDEO'], str(current_user.id), filename)
            # Make sure the output_file exists before sending
            if os.path.exists(output_file):
                return send_file(output_file, as_attachment=True)
            else:
                flash('File processing failed.')
                return redirect(request.url)
    return render_template('upload_video.html')

@app.route('/results')
@login_required
def user_results():
    user_id = str(current_user.id)
    image_results = os.listdir(os.path.join(app.config['OUTPUT_FOLDER_IMAGE'], user_id))
    video_results = os.listdir(os.path.join(app.config['OUTPUT_FOLDER_VIDEO'], user_id))
    return render_template('user_results.html', image_results=image_results, video_results=video_results)

@app.route('/download/<file_type>/<filename>')
@login_required
def download_file(file_type, filename):
    user_id = str(current_user.id)
    if file_type == 'image':
        folder = os.path.join(app.config['OUTPUT_FOLDER_IMAGE'], user_id)
    elif file_type == 'video':
        folder = os.path.join(app.config['OUTPUT_FOLDER_VIDEO'], user_id)
    else:
        flash('Invalid file type')
        return redirect(url_for('user_results'))
    
    file_path = os.path.join(folder, filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        flash('File not found')
        return redirect(url_for('user_results'))

if __name__ == '__main__':
    db.create_all()  # Create database tables
    app.run(debug=True, host='0.0.0.0', port=8000)
