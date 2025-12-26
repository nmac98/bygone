from flask import render_template
from . import main_bp
from models import Location, Route, LocationImage, ImageAsset

from sqlalchemy.orm import joinedload

@main_bp.route("/")
def index():
    locations = (
        Location.query
        .options(
            joinedload(Location.supabase_images)
            .joinedload(LocationImage.image)
            .joinedload(ImageAsset.files)
        )
        .all()
    )
    routes = Route.query.all()

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
        })

    # Location popup data: choose the first linked image by sort_order (if any)
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
            "main_image_url": main_image_url,  # <-- NEW
        })

    return render_template(
        "pages/index.html",
        locations=location_data,
        photos=photos,
        routes=routes,
    )