from flask import Flask, render_template, abort, request, url_for
import folium
import json
import os
from folium.features import DivIcon

app = Flask(__name__)

# Load locations from JSON once at startup
with open("data/locations.json", "r") as f:
    LOCATIONS = json.load(f)

def load_routes():
    with open(os.path.join('data', 'routes.json')) as f:
        return json.load(f)

routes = load_routes()

@app.route('/test')
def test():
    return "Flask is working!"

@app.route('/test_themes')
def test_themes():
    return {"routes": routes}

@app.route('/')
def index():
    # Center map on Dublin
    m = folium.Map(location=[53.3498, -6.2603], zoom_start=14)

    for loc in LOCATIONS:
        name = loc["name"]
        lat, lon = loc["lat"], loc["lon"]
        main_image = loc["images"][0]["file"]  # first image = cover
        loc_id = loc["id"]

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

@app.route("/gallery/<loc_id>")
def gallery(loc_id):

    loc = next((l for l in LOCATIONS if l["id"] == loc_id), None)
    if not loc:
        abort(404)

    # Create a mini folium map
    m = folium.Map(location=[loc["lat"], loc["lon"]], zoom_start=16)
    folium.Marker(
        [loc["lat"], loc["lon"]],
        popup=loc["name"],
        tooltip=loc["name"]
    ).add_to(m)

    map_html = m._repr_html_()  # generates the <iframe> HTML

    route_id = request.args.get("route")
    next_location = prev_location = None
    dialogue = None
    progress = None

    if route_id:
        route = next((r for r in routes if r["id"] == route_id), None)
        if route:
            stops = route["stops"]
            current_index = next(
                (i for i, stop in enumerate(stops) if stop["location_id"] == loc_id),
                None
            )

            if current_index is not None:
                dialogue = stops[current_index].get("dialogue", "")
                total_stops = len(stops)
                progress = f"Stop {current_index + 1} of {total_stops}"

                if current_index < len(stops) - 1:
                    next_id = stops[current_index + 1]["location_id"]
                    next_location = next(
                        (l for l in LOCATIONS if l["id"] == next_id),
                        None
                    )
                if current_index > 0:
                    prev_id = stops[current_index - 1]["location_id"]
                    prev_location = next(
                        (l for l in LOCATIONS if l["id"] == prev_id),
                        None
                    )

    return render_template("gallery.html", location=loc, map_html=map_html, next_location=next_location, prev_location=prev_location, dialogue=dialogue, route_id=route_id, progress=progress)

@app.route('/photo/<loc_id>/<photo_file>')
def photo_detail(loc_id, photo_file):
    # Find the location
    loc = next((l for l in LOCATIONS if l["id"] == loc_id), None)
    if not loc:
        abort(404)

    # Find index of current photo
    photos = loc["images"]
    current_index = next((i for i, p in enumerate(photos) if p["file"] == photo_file), None)
    if current_index is None:
        abort(404)

    # Determine previous and next photo files
    prev_photo = photos[current_index - 1]["file"] if current_index > 0 else None
    next_photo = photos[current_index + 1]["file"] if current_index < len(photos) - 1 else None

    return render_template(
        "photo_detail.html",
        location=loc,
        photo=photos[current_index],
        prev_photo=prev_photo,
        next_photo=next_photo
    )

@app.route("/route/<route_name>")
def view_route(route_name):
    route = next((r for r in routes if r['name'] == route_name), None)
    if not route:
        abort(404)

    # Load locations for this route
    with open(os.path.join('data', 'locations.json')) as f:
        locations = json.load(f)

    stops = []
    for stop in route['stops']:
        loc = next((l for l in locations if l['id'] == stop['location_id']), None)
        if loc:
            loc_copy = loc.copy()
            loc_copy['dialogue'] = stop['dialogue']
            stops.append(loc_copy)

    # Build Folium map with path line
    m = folium.Map(location=[stops[0]['lat'], stops[0]['lon']], zoom_start=14)

    coordinates = []
    for i, stop in enumerate(stops, start=1):
        coordinates.append((stop['lat'], stop['lon']))
        folium.Marker(
            [stop['lat'], stop['lon']],
            popup=f"<b>{stop['name']}</b><br>{stop['dialogue']}",
            tooltip=stop['name'],
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

if __name__ == "__main__":
    app.run(debug=True)