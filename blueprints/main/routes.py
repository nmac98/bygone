from flask import render_template
from . import main_bp
from models import Location, Route, Image
from utils.decorators import admin_required

@main_bp.route("/")
def index():
    locations = Location.query.all()
    routes = Route.query.all()

    photos = [
        {
            "id": p.id,
            "file": p.file,
            "title": p.title,
            "lat": p.lat,
            "lon": p.lon
        }
        for p in Image.query.filter(Image.lat.isnot(None), Image.lon.isnot(None)).all()
    ]


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
        photos=photos,
        routes=routes,
    )