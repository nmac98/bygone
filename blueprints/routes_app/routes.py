from flask import render_template, abort
from sqlalchemy.orm import joinedload
from . import routes_bp
from models import Route, RouteStop, Location

@routes_bp.route("/route/<route_name>")
def view_route(route_name):
    route = Route.query.options(
        joinedload(Route.stops).joinedload(RouteStop.location)
    ).filter_by(name=route_name).first()
    if not route:
        abort(404)

    stops = sorted(route.stops, key=lambda s: s.order)

    # Prepare stop data for Leaflet and stop cards
    stops_data = []
    for i, stop in enumerate(stops, start=1):
        loc = stop.location
        # Get first location image URL if available
        assets = loc.supabase_image_assets
        img_url = None
        if assets and assets[0].files:
            img_url = assets[0].files[0].public_url

        stops_data.append({
            "index": i,
            "name": loc.name,
            "lat": loc.lat,
            "lon": loc.lon,
            "dialogue": stop.dialogue,
            "img_url": img_url,
        })

    return render_template(
        "pages/route.html",
        route=route,
        stops=stops,
        stops_data=stops_data,
    )
