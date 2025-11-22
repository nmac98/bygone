from flask import render_template, abort
from . import photos_bp
from models import Location

@photos_bp.route('/photo/<loc_id>/<photo_file>')
def photo_detail(loc_id, photo_file):
    # Find the location
    loc = Location.query.get(loc_id)
    if not loc:
        abort(404)

    # Find index of current photo
    photos = loc.images
    if not photos:
        abort(404)

    current_index = next((i for i, p in enumerate(photos) if p.file == photo_file), None)
    if current_index is None:
        abort(404)

    # Determine previous and next photo files
    prev_photo = photos[current_index - 1].file if current_index > 0 else None
    next_photo = photos[current_index + 1].file if current_index < len(photos) - 1 else None

    return render_template(
        "pages/photo_detail.html",
        location=loc,
        photo=photos[current_index],
        prev_photo=prev_photo,
        next_photo=next_photo
    )
