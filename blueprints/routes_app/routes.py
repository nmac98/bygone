from flask import render_template, abort
from . import routes_bp
from models import Route
import folium
from folium.features import DivIcon

@routes_bp.route("/route/<route_name>")
def view_route(route_name):
    route = Route.query.filter_by(name=route_name).first()
    if not route:
        abort(404)

    stops = sorted(route.stops, key=lambda s: s.order)
    first_loc = stops[0].location
    m = folium.Map(location=[first_loc.lat, first_loc.lon], zoom_start=14)

    for i, stop in enumerate(stops, start=1):
        loc = stop.location
        folium.Marker(
            [loc.lat, loc.lon],
            popup=f"<b>{loc.name}</b><br>{stop.dialogue}",
            tooltip=loc.name,
            icon=DivIcon(
                icon_size=(30, 30),
                icon_anchor=(15, 15),
                html=f"""
                <div style="
                    background-color: #007bff;
                    color: white;
                    border-radius: 50%;
                    text-align: center;
                    font-weight: bold;
                    line-height: 30px;
                    width: 30px;
                    height: 30px;
                    border: 2px solid white;
                    box-shadow: 0 0 3px rgba(0,0,0,0.3);
                ">{i}</div>
                """
            )
        ).add_to(m)

    return render_template('route.html', route=route, stops=stops, map_html=m._repr_html_())
