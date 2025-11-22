from flask import render_template
from . import main_bp
from models import Location, Route
from utils.decorators import admin_required

@main_bp.route('/admin_test')
@admin_required
def test():
    return "Welcome, admin user!"

@main_bp.route('/test_themes')
def test_themes():
    routes = Route.query.all()
    return {"routes": [r.name for r in routes]}

@main_bp.route("/")
def index():
    locations = Location.query.all()
    routes = Route.query.all()

    # Prepare data for Leaflet/JS
    location_data = []
    for loc in locations:
        main_image = loc.images[0].file if loc.images else "placeholder.jpg"
        location_data.append({
            "id": loc.id,
            "name": loc.name,
            "lat": loc.lat,
            "lon": loc.lon,
            "description": loc.description,
            "main_image": main_image,
        })

    return render_template(
        "pages/index.html",
        locations=location_data,
        routes=routes,
    )