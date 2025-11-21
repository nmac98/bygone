from flask import Blueprint

photos_bp = Blueprint('photos', __name__)

from . import routes
