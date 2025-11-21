from flask import render_template, abort, request
from . import locations_bp
from models import Location, Route
import folium

@locations_bp.route("/gallery/<loc_id>")
def gallery(loc_id):

    loc = Location.query.get(loc_id)
    if not loc:
        abort(404)

    # Create a mini folium map
    m = folium.Map(location=[loc.lat, loc.lon], zoom_start=16)
    folium.Marker(
        [loc.lat, loc.lon],
        popup=loc.name,
        tooltip=loc.name
    ).add_to(m)

    map_html = m._repr_html_()  # generates the <iframe> HTML

    route_id = request.args.get("route")
    next_location = prev_location = None
    dialogue = None
    progress = None

    if route_id:
        route = Route.query.get(route_id)
        if route:
            stops = sorted(route.stops, key=lambda s: s.order)
            current_index = next(
                (i for i, stop in enumerate(stops) if stop.location_id == loc_id),
                None
            )

            if current_index is not None:
                dialogue = stops[current_index].dialogue
                total_stops = len(stops)
                progress = f"Stop {current_index + 1} of {total_stops}"

                if current_index < total_stops - 1:
                    next_location = stops[current_index + 1].location

                if current_index > 0:
                    prev_location = stops[current_index - 1].location

    return render_template(
        "gallery.html",
        location=loc,
        map_html=map_html,
        next_location=next_location,
        prev_location=prev_location,
        dialogue=dialogue,
        route_id=route_id,
        progress=progress
    )
