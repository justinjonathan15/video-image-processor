import os
import stripe
from flask import Flask, request, render_template, redirect, url_for, send_file, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

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
app.secret_key = secret_key
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

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

# User model for storing user data and tokens
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    tokens = db.Column(db.Integer, default=0)
    stripe_customer_id = db.Column(db.String(120))

db.create_all()

@app.route('/')
def index():
    return render_template('index.html', stripe_publishable_key=stripe_publishable_key)

@app.route('/charge', methods=['POST'])
def charge():
    amount = int(request.form['amount']) * 100  # amount in cents

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

    user = User.query.filter_by(email=request.form['stripeEmail']).first()
    if not user:
        user = User(email=request.form['stripeEmail'], stripe_customer_id=customer.id, tokens=amount // 100)
        db.session.add(user)
    else:
        user.tokens += amount // 100
    db.session.commit()

    session['email'] = user.email
    session['tokens'] = user.tokens
    return redirect(url_for('choose_upload'))

@app.route('/choose_upload')
def choose_upload():
    if not session.get('email'):
        return redirect(url_for('index'))
    return render_template('choose_upload.html')

@app.route('/upload_image', methods=['GET', 'POST'])
def upload_image():
    if not session.get('email'):
        return redirect(url_for('index'))

    user = User.query.filter_by(email=session['email']).first()
    if user.tokens <= 0:
        flash('You do not have enough tokens. Please purchase more.')
        return redirect(url_for('index'))

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_image_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['IMAGE_UPLOAD_FOLDER'], filename)
            file.save(filepath)
            # Process image file here or call your processing script
            os.system(f'python3 Image_AI_Keyworder.py')
            output_file = os.path.join(app.config['IMAGE_OUTPUT_FOLDER'], filename)
            # Deduct a token
            user.tokens -= 1
            db.session.commit()
            session['tokens'] = user.tokens
            # Make sure the output_file exists before sending
            if os.path.exists(output_file):
                return send_file(output_file, as_attachment=True)
            else:
                flash('File processing failed.')
                return redirect(request.url)
    return render_template('upload_image.html')

@app.route('/upload_video', methods=['GET', 'POST'])
def upload_video():
    if not session.get('email'):
        return redirect(url_for('index'))

    user = User.query.filter_by(email=session['email']).first()
    if user.tokens <= 0:
        flash('You do not have enough tokens. Please purchase more.')
        return redirect(url_for('index'))

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_video_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['VIDEO_UPLOAD_FOLDER'], filename)
            file.save(filepath)
            # Process video file here or call your processing script
            os.system(f'python3 Video_AI_Keyworder.py')
            output_file = os.path.join(app.config['VIDEO_OUTPUT_FOLDER'], filename)
            # Deduct a token
            user.tokens -= 1
            db.session.commit()
            session['tokens'] = user.tokens
            # Make sure the output_file exists before sending
            if os.path.exists(output_file):
                return send_file(output_file, as_attachment=True)
            else:
                flash('File processing failed.')
                return redirect(request.url)
    return render_template('upload_video.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8000)
