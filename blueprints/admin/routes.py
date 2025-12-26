from flask import render_template, request, url_for, redirect, flash
from utils.decorators import admin_required
from . import admin_bp
from models import Location, Route, RouteStop, ImageAsset, ImageFile, LocationImage
from extensions import db
from utils.ids import new_ulid
from utils.supabase_storage import upload_file_bytes, public_url, SUPABASE_BUCKET, delete_file
from sqlalchemy.orm import joinedload


from werkzeug.utils import secure_filename

#HELPER FOR FILE UPLOADS
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg"}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

@admin_bp.route('/')
@admin_required
def dashboard():
    return render_template('admin/dashboard.html')

@admin_bp.route('/locations')
@admin_required
def admin_locations():
    all_locations = Location.query.order_by(Location.name).all()
    return render_template('admin/locations.html', locations=all_locations)

@admin_bp.route('/location/new', methods=['GET', 'POST'])
@admin_required
def new_location():
    if request.method == 'POST':
        loc_id = request.form['id'].strip()
        name = request.form['name'].strip()
        description = request.form.get('description', '')

        if not loc_id:
            flash("Location ID is required.", "error")
            return redirect(request.url)

        # Ensure unique ID
        if Location.query.get(loc_id):
            flash("A location with that ID already exists.", "error")
            return redirect(request.url)

        # Lat/Lon as optional floats
        lat_raw = request.form.get('lat') or None
        lon_raw = request.form.get('lon') or None
        lat = float(lat_raw) if lat_raw else None
        lon = float(lon_raw) if lon_raw else None

        # Themes: comma-separated to list
        themes_raw = request.form.get('themes', '')
        themes = [t.strip() for t in themes_raw.split(',') if t.strip()]

        new_loc = Location(
            id=loc_id,
            name=name,
            description=description,
            lat=lat,
            lon=lon,
            themes=themes
        )

        db.session.add(new_loc)
        db.session.commit()

        flash("Location created.", "success")
        return redirect(url_for('admin.admin_locations'))

    return render_template('admin/location_new.html')

@admin_bp.route('/location/<location_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_location(location_id):

    location = Location.query.get_or_404(location_id)
    
    if request.method == 'POST':
        location.name = request.form['name'].strip()
        location.description = request.form.get('description', '')

        # Lat/lon as optional floats
        lat_raw = request.form.get('lat') or None
        lon_raw = request.form.get('lon') or None
        location.lat = float(lat_raw) if lat_raw else None
        location.lon = float(lon_raw) if lon_raw else None
    
        # Themes: comma-separated
        themes_raw = request.form.get('themes', '')
        themes = [t.strip() for t in themes_raw.split(',') if t.strip()]
        location.themes = themes

        db.session.commit()
        flash("Location updated.", "success")
        return redirect(url_for('admin.admin_locations'))   

    # Pre-populate themes as comma-separated string
    themes_text = ', '.join(location.themes or [])

    return render_template('admin/edit_location.html', location=location, themes_text=themes_text)

# delete location requires detaching any related photos and tour/route stops

@admin_bp.route('/location/<location_id>/delete', methods=['GET', 'POST'])
@admin_required
def delete_location(location_id):
    location = Location.query.get_or_404(location_id)

    # How many Supabase images are linked to this location?
    links = (
        LocationImage.query
        .options(joinedload(LocationImage.image).joinedload(ImageAsset.files))
        .filter_by(location_id=location_id)
        .all()
    )
    photo_count = len(links)

    # How many route stops use this location?
    stops = RouteStop.query.filter_by(location_id=location_id).all()
    stop_count = len(stops)

    if request.method == 'POST':

        # BLOCK deletion if still used in route stops
        if stop_count > 0:
            flash(
                "You can only remove a location when it is removed from all tour routes.",
                "error"
            )
            return redirect(url_for('admin_bp.delete_location', location_id=location_id))

        # Detach all linked images (delete join rows)
        LocationImage.query.filter_by(location_id=location_id).delete(synchronize_session=False)

        # Now delete the location
        db.session.delete(location)
        db.session.commit()

        flash("Location deleted and linked images detached.", "success")
        return redirect(url_for('admin_bp.admin_locations'))

    # For GET: show some useful info in the confirmation page.
    # Pass the LocationImage rows so you can display which images would be detached.
    return render_template(
        'admin/location_delete.html',
        location=location,
        photo_links=links,   # renamed from photos
        stops=stops,
        photo_count=photo_count,
        stop_count=stop_count
    )

@admin_bp.route('/route/new', methods=['GET', 'POST'])
@admin_required
def new_route():
    if request.method == 'POST':
        route_id = request.form['id'].strip()
        name = request.form['name'].strip()
        description = request.form.get('description', '')

        # Ensure unique ID
        if Route.query.get(route_id):
            flash("A route with that ID already exists.", "error")
            return redirect(request.url)

        new_r = Route(id=route_id, name=name, description=description)
        db.session.add(new_r)
        db.session.commit()

        flash("Route created.", "success")
        return redirect(url_for('admin.admin_routes'))

    return render_template('admin/route_new.html')

@admin_bp.route('/route/<route_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_route(route_id):
    route = Route.query.get_or_404(route_id)

    if request.method == 'POST':
        route.name = request.form['name'].strip()
        route.description = request.form.get('description', '')
        db.session.commit()

        flash("Route updated.", "success")
        return redirect(url_for('admin.admin_routes'))

    return render_template('admin/route_edit.html', route=route)

@admin_bp.route('/route/<route_id>/delete', methods=['GET', 'POST'])
@admin_required
def delete_route(route_id):
    route = Route.query.get_or_404(route_id)

    if request.method == 'POST':
        # Delete all route stops
        RouteStop.query.filter_by(route_id=route.id).delete()

        db.session.delete(route)
        db.session.commit()

        flash("Route deleted.", "success")
        return redirect(url_for('admin.admin_routes'))

    return render_template('admin/route_delete.html', route=route)

@admin_bp.route('/route/<route_id>/stops')
@admin_required
def manage_stops(route_id):
    route = Route.query.get_or_404(route_id)
    stops = route.stops  # already ordered

    return render_template(
        'admin/route_stops.html',
        route=route,
        stops=stops
    )

@admin_bp.route('/route/<route_id>/stops/new', methods=['GET', 'POST'])
@admin_required
def new_stop(route_id):
    route = Route.query.get_or_404(route_id)
    locations = Location.query.order_by(Location.name).all()

    if request.method == 'POST':
        location_id = request.form['location_id']
        dialogue = request.form.get('dialogue', '')

        # Determine next order position
        max_order = db.session.query(db.func.max(RouteStop.order))\
                              .filter_by(route_id=route_id).scalar()
        next_order = (max_order or 0) + 1

        new_s = RouteStop(
            order=next_order,
            dialogue=dialogue,
            route_id=route_id,
            location_id=location_id
        )

        db.session.add(new_s)
        db.session.commit()

        flash("Stop added.", "success")
        return redirect(url_for('admin.manage_stops', route_id=route_id))

    return render_template('admin/stop_new.html', route=route, locations=locations)

@admin_bp.route('/stop/<int:stop_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_stop(stop_id):
    stop = RouteStop.query.get_or_404(stop_id)
    locations = Location.query.order_by(Location.name).all()

    if request.method == 'POST':
        stop.location_id = request.form['location_id']
        stop.dialogue = request.form.get('dialogue', '')
        new_order = int(request.form['order'])

        # Only adjust if changed
        if new_order != stop.order:
            adjust_order(stop, new_order)

        db.session.commit()
        flash("Stop updated.", "success")
        return redirect(url_for('admin.manage_stops', route_id=stop.route_id))

    return render_template('admin/stop_edit.html', stop=stop, locations=locations)

def adjust_order(stop, new_order):
    route_id = stop.route_id
    old_order = stop.order

    # If moving down
    if new_order > old_order:
        affected = RouteStop.query.filter(
            RouteStop.route_id == route_id,
            RouteStop.order > old_order,
            RouteStop.order <= new_order
        ).all()
        for s in affected:
            s.order -= 1

    # If moving up
    elif new_order < old_order:
        affected = RouteStop.query.filter(
            RouteStop.route_id == route_id,
            RouteStop.order >= new_order,
            RouteStop.order < old_order
        ).all()
        for s in affected:
            s.order += 1

    stop.order = new_order

@admin_bp.route('/stop/<int:stop_id>/<direction>')
@admin_required
def move_stop(stop_id, direction):
    stop = RouteStop.query.get_or_404(stop_id)
    current_order = stop.order

    if direction == 'up':
        new_order = max(1, current_order - 1)
    else:
        # find max
        max_order = db.session.query(db.func.max(RouteStop.order))\
                               .filter_by(route_id=stop.route_id).scalar()
        new_order = min(max_order, current_order + 1)

    if new_order != current_order:
        adjust_order(stop, new_order)
        db.session.commit()

    return redirect(url_for('admin.manage_stops', route_id=stop.route_id))

@admin_bp.route('/stop/<int:stop_id>/delete', methods=['GET', 'POST'])
@admin_required
def delete_stop(stop_id):
    stop = RouteStop.query.get_or_404(stop_id)
    route_id = stop.route_id

    if request.method == 'POST':
        old_order = stop.order

        db.session.delete(stop)
        db.session.commit()

        # Re-collapse order numbers
        following = RouteStop.query.filter(
            RouteStop.route_id == route_id,
            RouteStop.order > old_order
        ).all()
        for s in following:
            s.order -= 1

        db.session.commit()

        flash("Stop deleted.", "success")
        return redirect(url_for('admin.manage_stops', route_id=route_id))

    return render_template('admin/stop_delete.html', stop=stop)

#new images functionality:
@admin_bp.route("/images")
@admin_required
def images_list():
    q = (request.args.get("q") or "").strip()
    query = ImageAsset.query

    if q:
        like = f"%{q}%"
        query = query.filter(ImageAsset.title.ilike(like))

    images = query.order_by(ImageAsset.created_at.desc()).all()
    return render_template("admin/images_list.html", images=images, search_query=q)


@admin_bp.route("/images/upload", methods=["GET", "POST"])
@admin_required
def images_upload():
    locations = Location.query.order_by(Location.name.asc()).all()

    if request.method == "POST":
        f = request.files.get("file")
        title = (request.form.get("title") or "").strip() or None
        date = (request.form.get("date") or "").strip() or None
        description = (request.form.get("description") or "").strip() or None
        lat_raw = (request.form.get("lat") or "").strip()
        lon_raw = (request.form.get("lon") or "").strip()
        location_id = (request.form.get("location_id") or "").strip() or None

        if not f or f.filename == "":
            flash("Please choose a file.", "error")
            return redirect(request.url)

        # Parse lat/lon (nullable)
        lat = None
        lon = None
        try:
            if lat_raw:
                lat = float(lat_raw)
            if lon_raw:
                lon = float(lon_raw)
        except ValueError:
            flash("Latitude / Longitude must be numbers.", "error")
            return redirect(request.url)

        image_id = new_ulid()
        filename = secure_filename(f.filename)
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"

        storage_key = f"original/{image_id}.{ext}"
        content = f.read()
        mime_type = f.mimetype

        # Upload to Supabase
        upload_file_bytes(
            storage_key=storage_key,
            content=content,
            content_type=mime_type,
        )

        # DB rows
        img = ImageAsset(
            id=image_id,
            title=title,
            date=date,
            description=description,
            lat=lat,
            lon=lon,
        )
        db.session.add(img)

        file_row = ImageFile(
            image_id=image_id,
            variant="original",
            bucket=SUPABASE_BUCKET,
            storage_key=storage_key,
            public_url=public_url(storage_key),
        )
        db.session.add(file_row)

        # Optional: link to a location (single for now)
        if location_id:
            link = LocationImage(location_id=location_id, image_id=image_id, sort_order=0)
            db.session.add(link)

        db.session.commit()
        flash("Uploaded image to Supabase.", "success")
        return redirect(url_for("admin.images_list"))

    return render_template("admin/images_upload.html", locations=locations)

@admin_bp.route("/images/<image_id>/attach", methods=["GET", "POST"])
@admin_required
def image_attach(image_id):
    img = ImageAsset.query.get_or_404(image_id)
    locations = Location.query.order_by(Location.name.asc()).all()

    if request.method == "POST":
        location_id = request.form.get("location_id")
        if not location_id:
            flash("Choose a location.", "error")
            return redirect(request.url)

        # find next sort order
        existing = LocationImage.query.filter_by(location_id=location_id).count()
        link = LocationImage(location_id=location_id, image_id=image_id, sort_order=existing)
        db.session.add(link)
        db.session.commit()

        flash("Attached image to location.", "success")
        return redirect(url_for("admin.images_list"))

    return render_template("admin/image_attach.html", img=img, locations=locations)

@admin_bp.route("/images/<image_id>/edit", methods=["GET", "POST"])
@admin_required
def images_edit(image_id):
    img = ImageAsset.query.get_or_404(image_id)
    locations = Location.query.order_by(Location.name.asc()).all()
    original = next((f for f in img.files if f.variant == "original"), None)
    current_link = next((rel for rel in img.locations), None)
    current_location_id = current_link.location_id if current_link else ""

    if request.method == "POST":
        title = (request.form.get("title") or "").strip() or None
        date = (request.form.get("date") or "").strip() or None
        description = (request.form.get("description") or "").strip() or None
        lat_raw = (request.form.get("lat") or "").strip()
        lon_raw = (request.form.get("lon") or "").strip()
        location_id = (request.form.get("location_id") or "").strip() or None
        new_file = request.files.get("file")

        # lat / lon
        lat = None
        lon = None
        try:
            if lat_raw:
                lat = float(lat_raw)
            if lon_raw:
                lon = float(lon_raw)
        except ValueError:
            flash("Latitude / Longitude must be numbers.", "error")
            return redirect(request.url)

        # update metadata
        img.title = title
        img.date = date
        img.description = description
        img.lat = lat
        img.lon = lon

        # update location link (single for now)
        LocationImage.query.filter_by(image_id=img.id).delete()
        if location_id:
            db.session.add(LocationImage(location_id=location_id, image_id=img.id, sort_order=0))

        # optional: replace file
        if new_file and new_file.filename:
            filename = secure_filename(new_file.filename)
            ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
            storage_key = f"original/{img.id}.{ext}"
            content = new_file.read()
            mime_type = new_file.mimetype

            # delete old file if exists
            if original:
                try:
                    delete_file(original.storage_key)
                except Exception:
                    # fail soft – DB will still point to new file
                    pass

                # re-use the same ImageFile row
                original.storage_key = storage_key
                original.public_url = public_url(storage_key)
                original.bucket = SUPABASE_BUCKET
            else:
                # no existing file row – create one
                original = ImageFile(
                    image_id=img.id,
                    variant="original",
                    bucket=SUPABASE_BUCKET,
                    storage_key=storage_key,
                    public_url=public_url(storage_key),
                )
                db.session.add(original)

            # upload new file
            upload_file_bytes(
                storage_key=storage_key,
                content=content,
                content_type=mime_type,
            )

        db.session.commit()
        flash("Image updated.", "success")
        return redirect(url_for("admin.images_list"))

    # GET
    lat_val = img.lat if img.lat is not None else ""
    lon_val = img.lon if img.lon is not None else ""

    return render_template(
        "admin/images_edit.html",
        img=img,
        original=original,
        locations=locations,
        current_location_id=current_location_id,
        lat_val=lat_val,
        lon_val=lon_val,
    )

@admin_bp.route("/images/<image_id>/delete", methods=["POST"])
@admin_required
def images_delete(image_id):
    img = ImageAsset.query.get_or_404(image_id)

    # delete files from Supabase
    for f in img.files:
        try:
            delete_file(f.storage_key)
        except Exception:
            # don't block on storage failure
            pass

    db.session.delete(img)  # cascades to ImageFile + LocationImage
    db.session.commit()
    flash("Image and associated files deleted.", "success")
    return redirect(url_for("admin.images_list"))

