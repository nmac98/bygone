import os
import base64
import json
import re

from flask import render_template, request, jsonify
from . import main_bp
from models import Location, Route, LocationImage, ImageAsset

from sqlalchemy.orm import joinedload

@main_bp.route("/")
def index():
    return render_template("pages/index.html")


@main_bp.route("/explore")
def explore():
    locations = (
        Location.query
        .options(
            joinedload(Location.supabase_images)
            .joinedload(LocationImage.image)
            .joinedload(ImageAsset.files)
        )
        .all()
    )

    photos_q = (
        ImageAsset.query
        .options(joinedload(ImageAsset.files))
        .filter(ImageAsset.lat.isnot(None), ImageAsset.lon.isnot(None))
        .all()
    )

    photos = []
    for p in photos_q:
        original = next((f for f in p.files if f.variant == "original"), None)
        photos.append({
            "id": p.id,
            "title": p.title,
            "lat": p.lat,
            "lon": p.lon,
            "url": original.public_url if original else None,
            "date": p.date,
            "description": p.description,
        })

    location_data = []
    for loc in locations:
        li_sorted = sorted(loc.supabase_images, key=lambda x: x.sort_order or 0)

        main_image_url = None
        if li_sorted:
            asset = li_sorted[0].image
            original = next((f for f in asset.files if f.variant == "original"), None)
            if original:
                main_image_url = original.public_url

        location_data.append({
            "id": loc.id,
            "name": loc.name,
            "lat": loc.lat,
            "lon": loc.lon,
            "description": loc.description,
            "main_image_url": main_image_url,
        })

    return render_template(
        "pages/explore.html",
        locations=location_data,
        photos=photos,
    )


@main_bp.route("/tours")
def tours():
    routes = Route.query.all()
    return render_template("pages/tours.html", routes=routes)


@main_bp.route("/plaques")
def plaques():
    return render_template("pages/plaques.html")


@main_bp.route("/plaques/analyze", methods=["POST"])
def analyze_plaque():
    import anthropic
    from PIL import Image
    import io

    file = request.files.get("image")
    if not file:
        return jsonify({"error": "No image provided."}), 400

    # Resize if image exceeds Anthropic's 5 MB base64 limit
    raw = file.read()
    img = Image.open(io.BytesIO(raw))
    img = img.convert("RGB")

    quality = 85
    max_bytes = 4 * 1024 * 1024  # 4 MB target to stay well under the 5 MB limit
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)

    while buf.tell() > max_bytes and quality > 30:
        quality -= 10
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)

    image_data = base64.standard_b64encode(buf.getvalue()).decode("utf-8")
    media_type = "image/jpeg"

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": image_data,
                    },
                },
                {
                    "type": "text",
                    "text": (
                        "This is a photo of a historical plaque, likely found on a building or monument in Dublin, Ireland. "
                        "Identify who or what is commemorated and provide a concise historical summary. "
                        "If the subject is an artist (painter, sculptor, writer, composer, etc.), also list up to 3 of their most notable works as exact titles suitable for a Wikipedia search. "
                        "Respond with a JSON object only, no markdown:\n"
                        "{\"name\": \"Name of person or event\", \"summary\": \"2-3 sentence historical summary\", \"works\": [\"Work Title 1\", \"Work Title 2\"]}\n"
                        "If the subject is not an artist, omit the works field or set it to an empty array. "
                        "If you cannot identify a plaque or read its text clearly, respond with:\n"
                        "{\"error\": \"Could not read the plaque clearly. Please try again with a closer, clearer photo.\"}"
                    )
                }
            ],
        }]
    )

    response_text = message.content[0].text.strip()

    try:
        result = json.loads(response_text)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if match:
            try:
                result = json.loads(match.group())
            except Exception:
                result = {"name": "Historical Plaque", "summary": response_text}
        else:
            result = {"name": "Historical Plaque", "summary": response_text}

    return jsonify(result)