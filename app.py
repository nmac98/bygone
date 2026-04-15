from flask import Flask
from dotenv import load_dotenv

from config import Config
from extensions import db, migrate
from extensions.login import login_manager
from auth.routes import auth

# Import blueprints
from blueprints.main import main_bp
from blueprints.locations import locations_bp
from blueprints.routes_app import routes_bp
from blueprints.admin import admin_bp

import os
import json as _json

load_dotenv()

app = Flask(__name__)
app.config.from_object(Config)

def _from_json(value):
    try:
        return _json.loads(value)
    except Exception:
        return []

app.jinja_env.filters['from_json'] = _from_json

app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024  # 10 MB max upload

db.init_app(app)
migrate.init_app(app, db)
login_manager.init_app(app)

# Register blueprints (no url_prefix so existing URLs stay the same)
app.register_blueprint(main_bp)        # '/', '/test', '/test_themes'
app.register_blueprint(locations_bp)   # '/gallery/...'
app.register_blueprint(routes_bp)
app.register_blueprint(auth)    # '/route/...'
app.register_blueprint(admin_bp)    # '/admin/...'  

if __name__ == "__main__":
    app.run(debug=True)
