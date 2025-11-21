from flask import Blueprint

routes_bp = Blueprint('routes_app', __name__)

from . import routes
