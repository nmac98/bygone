from flask import render_template, abort
from . import routes_bp
from models import Route

@routes_bp.route("/route/<route_name>")
def view_route(route_name):
    route = Route.query.filter_by(name=route_name).first()
    if not route:
        abort(404)

    # Sort stops by order
    stops = sorted(route.stops, key=lambda s: s.order)

    # Prepare stop data for Leaflet
    stops_data = []
    for i, stop in enumerate(stops, start=1):
        loc = stop.location
        stops_data.append({
            "index": i,
            "name": loc.name,
            "lat": loc.lat,
            "lon": loc.lon,
            "dialogue": stop.dialogue,
        })

    return render_template(
        "route.html",
        route=route,
        stops=stops,
        stops_data=stops_data  # <-- for Leaflet JS
    )
