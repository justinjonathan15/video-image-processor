import os
import stripe
import uuid
from flask import Flask, request, render_template, redirect, url_for, send_file, flash, session
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

# Get API keys from environment variables
openai_api_key = os.getenv("OPENAI_API_KEY")
secret_key = os.getenv("SECRET_KEY")
stripe_secret_key = os.getenv("STRIPE_SECRET_KEY")
stripe_publishable_key = os.getenv("STRIPE_PUBLISHABLE_KEY")

# Debug: Print to verify loading environment variables
print("Loaded OPENAI_API_KEY:", openai_api_key)
print("Loaded SECRET_KEY:", secret_key)
print("Loaded STRIPE_SECRET_KEY:", stripe_secret_key)
print("Loaded STRIPE_PUBLISHABLE_KEY:", stripe_publishable_key)

# Initialize the Flask application
app = Flask(__name__)

if not secret_key:
    raise ValueError("Secret key not found. Please set the SECRET_KEY environment variable.")

app.secret_key = secret_key

# Stripe configuration
stripe.api_key = stripe_secret_key

# Define the upload folders
IMAGE_UPLOAD_FOLDER = 'input/images'
IMAGE_OUTPUT_FOLDER = 'output/images'
VIDEO_UPLOAD_FOLDER = 'input/videos'
VIDEO_OUTPUT_FOLDER = 'output/videos'
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'mov', 'avi'}

# Ensure the input and output directories exist
os.makedirs(IMAGE_UPLOAD_FOLDER, exist_ok=True)
os.makedirs(IMAGE_OUTPUT_FOLDER, exist_ok=True)
os.makedirs(VIDEO_UPLOAD_FOLDER, exist_ok=True)
os.makedirs(VIDEO_OUTPUT_FOLDER, exist_ok=True)

app.config['IMAGE_UPLOAD_FOLDER'] = IMAGE_UPLOAD_FOLDER
app.config['IMAGE_OUTPUT_FOLDER'] = IMAGE_OUTPUT_FOLDER
app.config['VIDEO_UPLOAD_FOLDER'] = VIDEO_UPLOAD_FOLDER
app.config['VIDEO_OUTPUT_FOLDER'] = VIDEO_OUTPUT_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB

def allowed_image_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

def allowed_video_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_VIDEO_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html', stripe_publishable_key=stripe_publishable_key)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Handle user registration here
        session['user_id'] = str(uuid.uuid4())  # Simulate user ID creation
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/charge', methods=['POST'])
def charge():
    # Amount in cents
    amount = 500

    customer = stripe.Customer.create(
        email=request.form['stripeEmail'],
        source=request.form['stripeToken']
    )

    charge = stripe.Charge.create(
        customer=customer.id,
        amount=amount,
        currency='usd',
        description='File Upload Charge'
    )

    session['paid'] = True
    return redirect(url_for('upload'))

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    if not session.get('paid'):
        return redirect(url_for('index'))

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and (allowed_image_file(file.filename) or allowed_video_file(file.filename)):
            filename = secure_filename(file.filename)
            user_id = session.get('user_id', 'anonymous')
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            unique_filename = f"{user_id}_{timestamp}_{filename}"

            if allowed_image_file(filename):
                filepath = os.path.join(app.config['IMAGE_UPLOAD_FOLDER'], unique_filename)
                file.save(filepath)
                # Process image file here or call your processing script
                os.system(f'python3 Image_AI_Keyworder.py')
                output_file = os.path.join(app.config['IMAGE_OUTPUT_FOLDER'], unique_filename)
            elif allowed_video_file(filename):
                filepath = os.path.join(app.config['VIDEO_UPLOAD_FOLDER'], unique_filename)
                file.save(filepath)
                # Process video file here or call your processing script
                os.system(f'python3 Video_AI_Keyworder.py')
                output_file = os.path.join(app.config['VIDEO_OUTPUT_FOLDER'], unique_filename)
            # Make sure the output_file exists before sending
            if os.path.exists(output_file):
                return redirect(url_for('success', filename=unique_filename))
            else:
                flash('File processing failed.')
                return redirect(request.url)
    return render_template('upload.html')

@app.route('/success')
def success():
    filename = request.args.get('filename')
    return render_template('success.html', filename=filename)

@app.route('/results')
def results():
    user_id = session.get('user_id', 'anonymous')
    files = []
    for folder in [app.config['IMAGE_OUTPUT_FOLDER'], app.config['VIDEO_OUTPUT_FOLDER']]:
        for file in os.listdir(folder):
            if file.startswith(user_id):
                file_path = os.path.join(folder, file)
                file_age = datetime.now() - datetime.fromtimestamp(os.path.getmtime(file_path))
                if file_age < timedelta(days=1):  # Keep files for 1 day
                    files.append(file)
                else:
                    os.remove(file_path)  # Delete old files
    return render_template('results.html', files=files)

@app.route('/download/<filename>')
def download(filename):
    user_id = session.get('user_id', 'anonymous')
    if not filename.startswith(user_id):
        return "Unauthorized", 403

    if allowed_image_file(filename):
        file_path = os.path.join(app.config['IMAGE_OUTPUT_FOLDER'], filename)
    elif allowed_video_file(filename):
        file_path = os.path.join(app.config['VIDEO_OUTPUT_FOLDER'], filename)
    else:
        return "File type not allowed", 400

    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return "File not found", 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)
