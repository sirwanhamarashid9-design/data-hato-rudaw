# هاتووی ڕووداوی ڕۆژانە — Online Web App

## Run locally for testing
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
python app.py

Then open http://127.0.0.1:5000

## Production
Deploy this folder to a Python hosting service supporting Flask/Gunicorn. Set SECRET_KEY to a strong random value. Use HTTPS. Persistent storage is required for database.db and uploads/. For multiple devices, all users must access the same deployed URL.

Default Super Admin: admin / Admin@123 (change it before production).
