from app import db, create_app

# Create an application context
app = create_app()
with app.app_context():
    db.create_all()
    print("Database initialized successfully!")

