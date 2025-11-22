from flask import render_template, abort, request
from . import locations_bp
from models import Location, Route

@locations_bp.route("/gallery/<loc_id>")
def gallery(loc_id):

    loc = Location.query.get(loc_id)
    if not loc:
        abort(404)

    map_data = {
        "lat": loc.lat,
        "lon": loc.lon,
        "name": loc.name,
    }

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
        "pages/gallery.html",
        location=loc,
        map_data=map_data,
        next_location=next_location,
        prev_location=prev_location,
        dialogue=dialogue,
        route_id=route_id,
        progress=progress
    )
