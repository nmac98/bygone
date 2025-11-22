from flask import render_template, request, url_for, redirect
from utils.decorators import admin_required
from . import admin_bp
from models import Location
from extensions import db

@admin_bp.route('/')
@admin_required
def dashboard():
    return render_template('admin/dashboard.html')

@admin_bp.route('/locations')
@admin_required
def admin_locations():
    all_locations = Location.query.all()
    return render_template('admin/locations.html', locations=all_locations)

@admin_bp.route('/routes')
@admin_required
def admin_routes():
    return "Routes management coming soon"

@admin_bp.route('/location/<location_id>/edit', methods=['GET', 'POST'] )
@admin_required
def edit_location(location_id):

    location = Location.query.get_or_404(location_id)
    
    if request.method =='POST':
        # Process form data and update location
        location.name = request.form['name']
        location.lat = request.form['lat']
        location.lon = request.form['lon']
        location.description = request.form['description']
    
        #themes: treat as comma separated text for now
        themes = request.form['themes'].split(',')
        location.themes = [t.strip() for t in themes if t.strip()]
        db.session.commit()

        return redirect(url_for('admin.admin_locations'))   

    return render_template('admin/edit_location.html', location=location)   