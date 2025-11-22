from flask import render_template
from utils.decorators import admin_required
from . import admin_bp

@admin_bp.route('/')
@admin_required
def dashboard():
    return render_template('admin/dashboard.html')

@admin_bp.route('/locations')
@admin_required
def admin_locations():
    return "Locations management coming soon"

@admin_bp.route('/routes')
@admin_required
def admin_routes():
    return "Routes management coming soon"
