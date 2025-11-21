from flask import render_template
from . import main_bp
from models import Location, Route
import folium

@main_bp.route('/test')
def test():
    return "Flask is working!"

@main_bp.route('/test_themes')
def test_themes():
    routes = Route.query.all()
    return {"routes": [r.name for r in routes]}

@main_bp.route('/')
def index():
    # Center map on Dublin
    locations = Location.query.all()
    routes = Route.query.all()
    
    m = folium.Map(location=[53.3498, -6.2603], zoom_start=14)

    for loc in locations:
        name = loc.name
        lat, lon = loc.lat, loc.lon
        main_image = loc.images[0].file if loc.images else "placeholder.jpg"  # first image = cover
        loc_id = loc.id

        popup_html = f"""
        <b>{name}</b><br>
        <img src="/static/images/{main_image}" width="200"><br>
        <a href="/gallery/{loc_id}" target="_blank">See more photos</a>
        """

        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_html, max_width=250),
            tooltip=name
        ).add_to(m)

    return render_template("index.html", folium_map=m._repr_html_(), routes=routes)
