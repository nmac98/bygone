from flask import Flask, render_template, abort
import folium
import json
import os

app = Flask(__name__)

# Load locations from JSON once at startup
with open("data/locations.json", "r") as f:
    LOCATIONS = json.load(f)

def load_themes():
    with open(os.path.join('data', 'themes.json')) as f:
        return json.load(f)

themes = load_themes()

@app.route('/test')
def test():
    return "Flask is working!"

@app.route('/test_themes')
def test_themes():
    return {"themes": themes}

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

    return render_template("index.html", folium_map=m._repr_html_(), themes=themes)

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

    return render_template("gallery.html", location=loc, map_html=map_html)

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

@app.route("/theme/<theme_name>")
def theme_map(theme_name):
    # Include locations where the theme is in the location's themes list
    themed_locations = [loc for loc in LOCATIONS if theme_name in loc.get("themes", [])]

    # Folium map centered on Dublin
    m = folium.Map(location=[53.349805, -6.26031], zoom_start=13)


    # Add markers
    for loc in themed_locations:
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

    

    map_html = m._repr_html_()
    return render_template("theme_map.html", theme_name=theme_name, map_html=map_html)


if __name__ == "__main__":
    app.run(debug=True)