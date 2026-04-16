import os
from flask import render_template, request, url_for, redirect, flash, current_app
from utils.decorators import admin_required
from . import admin_bp
from models import Location, Route, RouteStop, ImageAsset, ImageFile, LocationImage, LocationChapter, ChapterBlock, Topic, ChapterTopic, LocationCategory
from extensions import db
from utils.ids import new_ulid
from utils.supabase_storage import upload_file_bytes, public_url, SUPABASE_BUCKET, delete_file
from sqlalchemy.orm import joinedload


from werkzeug.utils import secure_filename

#HELPER FOR FILE UPLOADS
ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg"}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_IMAGE_EXTENSIONS

def get_static_images():
    images_dir = os.path.join(current_app.static_folder, 'images')
    return sorted([
        f for f in os.listdir(images_dir)
        if f.rsplit('.', 1)[-1].lower() in ALLOWED_IMAGE_EXTENSIONS
    ])

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

        cat_raw = (request.form.get('category') or '').strip()
        try:
            category = LocationCategory(cat_raw) if cat_raw else LocationCategory.POI
        except ValueError:
            category = LocationCategory.POI

        new_loc = Location(
            id=loc_id,
            name=name,
            description=description,
            lat=lat,
            lon=lon,
            themes=themes,
            category=category
        )

        db.session.add(new_loc)
        db.session.commit()

        flash("Location created.", "success")
        return redirect(url_for('admin.admin_locations'))
    
    categories = list(LocationCategory)
    return render_template('admin/location_new.html', categories=categories, default_category=LocationCategory.POI.value)

@admin_bp.route('/location/<location_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_location(location_id):
    location = Location.query.options(
        joinedload(Location.chapters)
            .joinedload(LocationChapter.blocks)
            .joinedload(ChapterBlock.image_asset)
            .joinedload(ImageAsset.files),
        joinedload(Location.supabase_images)
            .joinedload(LocationImage.image)
            .joinedload(ImageAsset.files),
    ).get_or_404(location_id)

    if request.method == 'POST':
        location.name = request.form['name'].strip()
        location.description = request.form.get('description', '')

        lat_raw = request.form.get('lat') or None
        lon_raw = request.form.get('lon') or None
        location.lat = float(lat_raw) if lat_raw else None
        location.lon = float(lon_raw) if lon_raw else None

        themes_raw = request.form.get('themes', '')
        themes = [t.strip() for t in themes_raw.split(',') if t.strip()]
        location.themes = themes

        cat_raw = (request.form.get('category') or '').strip()
        try:
            location.category = LocationCategory(cat_raw) if cat_raw else LocationCategory.POI
        except ValueError:
            location.category = LocationCategory.POI

        db.session.commit()
        flash("Location updated.", "success")
        return redirect(url_for('admin.edit_location', location_id=location_id))

    themes_text = ', '.join(location.themes or [])
    categories = list(LocationCategory)
    all_images = ImageAsset.query.order_by(ImageAsset.created_at.desc()).limit(300).all()
    topics = Topic.query.order_by(Topic.title.asc()).all()

    return render_template(
        'admin/edit_location.html',
        location=location,
        themes_text=themes_text,
        categories=categories,
        all_images=all_images,
        topics=topics,
    )

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
            return redirect(url_for('admin.delete_location', location_id=location_id))

        # Detach all linked images (delete join rows)
        LocationImage.query.filter_by(location_id=location_id).delete(synchronize_session=False)

        #detach chapters 
        LocationChapter.query.filter_by(location_id=location_id).delete(synchronize_session=False)

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

@admin_bp.route("/routes")
@admin_required
def admin_routes():
    routes = Route.query.order_by(Route.id.asc()).all()
    return render_template(
        "admin/routes_list.html",
        routes=routes
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

        cover_image = request.form.get('cover_image', '').strip() or None
        route_type = request.form.get('route_type', 'walking').strip()
        if route_type not in ('walking', 'running'):
            route_type = 'walking'
        new_r = Route(id=route_id, name=name, description=description, cover_image=cover_image, route_type=route_type)
        db.session.add(new_r)
        db.session.commit()

        flash("Route created.", "success")
        return redirect(url_for('admin.admin_routes'))

    images = ImageAsset.query.options(joinedload(ImageAsset.files)).order_by(ImageAsset.created_at.desc()).all()
    return render_template('admin/route_new.html', images=images)

@admin_bp.route('/route/<route_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_route(route_id):
    route = Route.query.get_or_404(route_id)

    if request.method == 'POST':
        route.name = request.form['name'].strip()
        route.description = request.form.get('description', '')
        route.cover_image = request.form.get('cover_image', '').strip() or None
        route_type = request.form.get('route_type', 'walking').strip()
        route.route_type = route_type if route_type in ('walking', 'running') else 'walking'
        db.session.commit()

        flash("Route updated.", "success")
        return redirect(url_for('admin.admin_routes'))

    images = ImageAsset.query.options(joinedload(ImageAsset.files)).order_by(ImageAsset.created_at.desc()).all()
    return render_template('admin/route_edit.html', route=route, images=images)

@admin_bp.route('/route/<route_id>/waypoints', methods=['GET', 'POST'])
@admin_required
def route_waypoints(route_id):
    import json as _json
    route = Route.query.get_or_404(route_id)
    stops = sorted(route.stops, key=lambda s: s.order)

    if request.method == 'POST':
        payload = request.get_json() or {}
        wps = payload.get('waypoints', [])
        # Validate: each must have lat, lon, after_stop
        clean = []
        for w in wps:
            try:
                clean.append({
                    'lat':        float(w['lat']),
                    'lon':        float(w['lon']),
                    'after_stop': int(w['after_stop']),
                })
            except (KeyError, ValueError, TypeError):
                continue
        route.waypoints = clean
        db.session.commit()
        return {'ok': True}

    stops_data = [{'name': s.location.name, 'lat': s.location.lat, 'lon': s.location.lon}
                  for s in stops]
    return render_template('admin/route_waypoints.html',
                           route=route,
                           stops_data=stops_data,
                           waypoints=route.waypoints or [])


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

@admin_bp.route('/stop/<int:stop_id>/dialogue/save', methods=['POST'])
@admin_required
def stop_dialogue_save(stop_id):
    stop = RouteStop.query.get_or_404(stop_id)
    data = request.get_json()
    stop.dialogue = (data or {}).get('dialogue', stop.dialogue)
    db.session.commit()
    return {'ok': True}


@admin_bp.route('/route/<route_id>/dialogue')
@admin_required
def route_dialogue(route_id):
    route = Route.query.get_or_404(route_id)
    stops = (
        RouteStop.query
        .filter_by(route_id=route_id)
        .options(
            joinedload(RouteStop.location)
                .joinedload(Location.chapters)
                .joinedload(LocationChapter.blocks)
        )
        .order_by(RouteStop.order)
        .all()
    )
    return render_template('admin/route_dialogue.html', route=route, stops=stops)


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
    preselected_location_id = request.args.get("location_id", "")

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
        if location_id:
            return redirect(url_for("admin.edit_location", location_id=location_id))
        return redirect(url_for("admin.images_list"))

    return render_template("admin/images_upload.html", locations=locations,
                           preselected_location_id=preselected_location_id)

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

# ==========================================================
# === CHAPTERS FEATURE: NEW ROUTES BELOW ====================
# ==========================================================

@admin_bp.route("/location/<location_id>/chapters")
@admin_required
def chapters_for_location(location_id):
    """
    List chapters for a location.
    """
    location = Location.query.options(
        joinedload(Location.chapters)
    ).get_or_404(location_id)

    return render_template("admin/chapters_list.html", location=location)


@admin_bp.route("/location/<location_id>/chapters/new", methods=["GET", "POST"])
@admin_required
def chapter_new(location_id):
    """
    Create a new chapter for a location.
    """
    location = Location.query.get_or_404(location_id)

    if request.method == "POST":
        title = (request.form.get("title") or "").strip()
        summary = (request.form.get("summary") or "").strip() or None
        sort_order = int(request.form.get("sort_order") or 0)

        if not title:
            flash("Title is required.", "error")
            return redirect(request.url)

        ch = LocationChapter(
            location_id=location.id,
            title=title,
            summary=summary,
            sort_order=sort_order,
        )
        db.session.add(ch)
        db.session.commit()

        flash("Chapter created.", "success")
        return redirect(url_for("admin.edit_location", location_id=location.id))

    return render_template("admin/chapter_new.html", location=location)


@admin_bp.route("/chapters/<int:chapter_id>/edit", methods=["GET", "POST"])
@admin_required
def chapter_edit(chapter_id):
    """
    Edit chapter metadata, manage blocks, and manage 'find out more' topic links.
    """
    chapter = LocationChapter.query.options(
        joinedload(LocationChapter.blocks).joinedload(ChapterBlock.image_asset),
        joinedload(LocationChapter.chapter_topics).joinedload(ChapterTopic.topic),
        joinedload(LocationChapter.location),
    ).get_or_404(chapter_id)

    if request.method == "POST":
        chapter.title = (request.form.get("title") or "").strip()
        chapter.summary = (request.form.get("summary") or "").strip() or None
        chapter.sort_order = int(request.form.get("sort_order") or 0)

        if not chapter.title:
            flash("Title is required.", "error")
            return redirect(request.url)

        db.session.commit()
        flash("Chapter updated.", "success")
        return redirect(url_for("admin.edit_location", location_id=chapter.location_id))

    # Topics library for attach dropdown
    topics = Topic.query.order_by(Topic.title.asc()).all()

    # Images for block creation dropdown (optional but useful)
    images = ImageAsset.query.order_by(ImageAsset.created_at.desc()).limit(300).all()

    return render_template(
        "admin/chapter_edit.html",
        chapter=chapter,
        topics=topics,
        images=images,
    )


@admin_bp.route("/chapters/<int:chapter_id>/delete", methods=["POST"])
@admin_required
def chapter_delete(chapter_id):
    chapter = LocationChapter.query.get_or_404(chapter_id)
    location_id = chapter.location_id
    db.session.delete(chapter)
    db.session.commit()
    flash("Chapter deleted.", "success")
    return redirect(url_for("admin.edit_location", location_id=location_id))


# -----------------------
# Blocks
# -----------------------
@admin_bp.route("/chapters/<int:chapter_id>/blocks/new", methods=["GET", "POST"])
@admin_required
def block_new(chapter_id):
    chapter = LocationChapter.query.options(joinedload(LocationChapter.location)).get_or_404(chapter_id)
    images = ImageAsset.query.order_by(ImageAsset.created_at.desc()).limit(300).all()

    if request.method == "POST":
        block_type = (request.form.get("block_type") or "").strip()
        sort_order = int(request.form.get("sort_order") or 0)

        if block_type == "people":
            import json as _json
            raw = (request.form.get("people_body") or "").strip()
            try:
                people_data = _json.loads(raw)
                body_val = _json.dumps(people_data) if isinstance(people_data, list) else None
            except Exception:
                body_val = None
        else:
            body_val = (request.form.get("body") or "").strip() or None

        b = ChapterBlock(
            chapter_id=chapter.id,
            block_type=block_type,
            sort_order=sort_order,
            body=body_val,
            caption_override=(request.form.get("caption_override") or "").strip() or None,
            link_label=(request.form.get("link_label") or "").strip() or None,
            link_url=(request.form.get("link_url") or "").strip() or None,
            link_note=(request.form.get("link_note") or "").strip() or None,
        )

        image_id = (request.form.get("image_asset_id") or "").strip()
        if image_id:
            b.image_asset_id = image_id

        # light validation per type
        if block_type == "text" and not b.body:
            flash("Text block requires content.", "error")
            return redirect(request.url)

        if block_type == "link" and not b.link_url:
            flash("Link block requires a URL.", "error")
            return redirect(request.url)

        if block_type == "image" and not b.image_asset_id:
            flash("Image block requires an image selection.", "error")
            return redirect(request.url)

        if block_type == "people" and not b.body:
            flash("People block requires at least one person. Generate or add people first.", "error")
            return redirect(request.url)

        if block_type not in ("text", "image", "link", "divider", "people"):
            flash("Invalid block type.", "error")
            return redirect(request.url)

        db.session.add(b)
        db.session.commit()
        flash("Block created.", "success")
        return redirect(url_for("admin.edit_location", location_id=chapter.location_id))

    preset_type = request.args.get("block_type", "")
    return render_template("admin/block_new.html", chapter=chapter, images=images, preset_type=preset_type)


@admin_bp.route("/blocks/<int:block_id>/delete", methods=["POST"])
@admin_required
def block_delete(block_id):
    b = ChapterBlock.query.get_or_404(block_id)
    location_id = b.chapter.location_id
    db.session.delete(b)
    db.session.commit()
    flash("Block deleted.", "success")
    return redirect(url_for("admin.edit_location", location_id=location_id))


@admin_bp.route("/blocks/<int:block_id>/people/edit", methods=["GET", "POST"])
@admin_required
def block_people_edit(block_id):
    import json as _json
    b = ChapterBlock.query.options(
        joinedload(ChapterBlock.chapter).joinedload(LocationChapter.location)
    ).get_or_404(block_id)

    if request.method == "POST":
        # Support both AJAX (JSON body) and form POST
        if request.is_json:
            payload = request.get_json() or {}
            people = payload.get("people", [])
        else:
            body = (request.form.get("body") or "").strip()
            try:
                people = _json.loads(body)
            except Exception:
                people = []
        if not isinstance(people, list):
            people = []
        b.body = _json.dumps(people)
        db.session.commit()
        if request.is_json:
            return {"ok": True}
        flash("People block saved.", "success")
        return redirect(url_for("admin.edit_location", location_id=b.chapter.location_id))

    try:
        people = _json.loads(b.body or "[]")
    except Exception:
        people = []

    return render_template(
        "admin/block_people_edit.html",
        block=b,
        chapter=b.chapter,
        people=people,
    )


# -----------------------
# Topics library
# -----------------------
@admin_bp.route("/topics")
@admin_required
def topics_list():
    topics = Topic.query.order_by(Topic.title.asc()).all()
    return render_template("admin/topics_list.html", topics=topics)


@admin_bp.route("/topics/new", methods=["GET", "POST"])
@admin_required
def topic_new():
    if request.method == "POST":
        slug = (request.form.get("slug") or "").strip()
        title = (request.form.get("title") or "").strip()
        summary = (request.form.get("summary") or "").strip() or None
        default_url = (request.form.get("default_url") or "").strip()

        if not slug or not title or not default_url:
            flash("Slug, title, and default URL are required.", "error")
            return redirect(request.url)

        # prevent duplicate slug
        if Topic.query.filter_by(slug=slug).first():
            flash("That slug already exists.", "error")
            return redirect(request.url)

        t = Topic(slug=slug, title=title, summary=summary, default_url=default_url)
        db.session.add(t)
        db.session.commit()
        flash("Topic created.", "success")
        return redirect(url_for("admin.topics_list"))

    return render_template("admin/topic_new.html")


@admin_bp.route("/topics/<int:topic_id>/delete", methods=["POST"])
@admin_required
def topic_delete(topic_id):
    t = Topic.query.get_or_404(topic_id)
    db.session.delete(t)
    db.session.commit()
    flash("Topic deleted.", "success")
    return redirect(url_for("admin.topics_list"))


# -----------------------
# Attach / detach topics to chapter
# -----------------------
@admin_bp.route("/chapters/<int:chapter_id>/topics/attach", methods=["POST"])
@admin_required
def chapter_topic_attach(chapter_id):
    chapter = LocationChapter.query.get_or_404(chapter_id)

    topic_id = request.form.get("topic_id")
    if not topic_id:
        flash("Pick a topic.", "error")
        return redirect(url_for("admin.chapter_edit", chapter_id=chapter.id))

    # prevent duplicates
    existing = ChapterTopic.query.filter_by(chapter_id=chapter.id, topic_id=int(topic_id)).first()
    if existing:
        flash("That topic is already attached to this chapter.", "error")
        return redirect(url_for("admin.chapter_edit", chapter_id=chapter.id))

    ct = ChapterTopic(
        chapter_id=chapter.id,
        topic_id=int(topic_id),
        sort_order=int(request.form.get("sort_order") or 0),
        label_override=(request.form.get("label_override") or "").strip() or None,
        note=(request.form.get("note") or "").strip() or None,
    )
    db.session.add(ct)
    db.session.commit()
    flash("Topic attached.", "success")
    return redirect(url_for("admin.edit_location", location_id=chapter.location_id))


@admin_bp.route("/ai/draft", methods=["POST"])
@admin_required
def ai_draft():
    import anthropic
    data = request.get_json()
    field_type      = (data or {}).get("field_type", "")
    location_name   = (data or {}).get("location_name", "")
    chapter_title   = (data or {}).get("chapter_title", "")
    extra_context   = (data or {}).get("extra_context", "")
    existing_text   = (data or {}).get("existing_text", "")

    def ctx(lines):
        return "\n".join(l for l in lines if l.strip())

    if field_type == "location_description":
        prompt = ctx([
            f'Write a 2–3 sentence overview description of "{location_name}", a Dublin heritage location, for visitors using a history app.',
            "Be engaging, factual, and concise. Write in the present tense.",
            f"Additional context: {extra_context}" if extra_context else "",
            f"Improve on this existing draft: {existing_text}" if existing_text else "",
            "Reply with the description only — no preamble, no quotes.",
        ])
    elif field_type == "chapter_summary":
        prompt = ctx([
            f'Write a 1–2 sentence intro summary for a history chapter titled "{chapter_title}" about {location_name} in Dublin.',
            "It appears in italics at the top of the chapter as a brief orientation for the reader.",
            f"Additional context: {extra_context}" if extra_context else "",
            "Reply with the summary only — no preamble, no quotes.",
        ])
    elif field_type == "text_block":
        prompt = ctx([
            f'Write a paragraph of historical content for a chapter titled "{chapter_title}" about {location_name} in Dublin.',
            "Audience: curious visitors using a heritage app. Be accurate, vivid, and accessible. 3–5 sentences.",
            f"Focus on: {extra_context}" if extra_context else "",
            f"Expand or improve on this draft: {existing_text}" if existing_text else "",
            "Reply with the paragraph only — no preamble, no quotes.",
        ])
    elif field_type == "people_cards":
        prompt = ctx([
            f'List the 6–8 most notable people associated with "{location_name}" in Dublin'
            + (f', specifically in the context of "{chapter_title}"' if chapter_title else '') + '.',
            f'Additional focus: {extra_context}' if extra_context else '',
            '',
            'Return a JSON array only — no markdown, no explanation, no code fences.',
            'Each item must follow this exact structure:',
            '{"name": "Full Name", "dates": "YYYY–YYYY", "role": "One-line role or profession", "summary": "2–3 sentences on their connection to this place and their notable achievements."}',
            'Use "YYYY–YYYY" date format (en dash). Use empty string if dates are unknown.',
            'Be accurate. Only include people with a genuine, documented connection to this location.',
        ])
    elif field_type == "stop_dialogue":
        route_name      = (data or {}).get("route_name", "")
        stop_number     = (data or {}).get("stop_number", "")
        chapters        = (data or {}).get("chapters", [])
        next_location   = (data or {}).get("next_location_name", "")
        chapter_ctx     = "; ".join(chapters) if chapters else ""
        is_last_stop    = not next_location

        prompt = ctx([
            f'You are writing the spoken tour guide script for stop {stop_number} of a walking tour called "{route_name}" in Dublin, Ireland.',
            f'The stop is at "{location_name}".',
            f'Location overview: {extra_context}' if extra_context else "",
            f'History chapters at this location: {chapter_ctx}' if chapter_ctx else "",
            "",
            "TONE AND STYLE:",
            "- Factual and detail-driven. Specific details — names, dates, materials, dimensions, events — are the backbone of good storytelling. Prefer the concrete over the abstract.",
            "- Storytelling in voice, not in gimmick. No rhetorical flourishes, no clichés ('a city frozen in time', 'let that sink in', 'stands as a testament to', 'hidden gem', 'nestled', 'fascinatingly').",
            "- Written to be spoken aloud to a small group standing at the location. Natural sentence rhythm, not written prose.",
            "- 2–3 paragraphs. No headings, no bullet points.",
            "",
            "CLOSING:",
            f'The final sentence should briefly and naturally signal the move to the next stop: "{next_location}". '
            "Do this with variety — sometimes a thematic contrast, sometimes a time-period shift, sometimes a simple geographical cue. "
            "Do not always frame it the same way. Do not name the next stop explicitly, but give the listener a sense of what kind of place or era they are moving toward."
            if not is_last_stop else
            "This is the final stop. Close with a short reflection that brings the tour to a natural end — something that looks back across what was seen, without being sentimental.",
            "",
            f"Improve on this existing draft: {existing_text}" if existing_text else "",
            "Reply with the dialogue only — no preamble, no quotation marks.",
        ])
    else:
        return {"error": "Unknown field type."}, 400

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    max_tokens = 1200 if field_type == "people_cards" else 800
    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text.strip()

    if field_type == "people_cards":
        import json as _json
        try:
            people = _json.loads(raw)
            return {"people": people}
        except Exception:
            return {"error": "AI returned invalid JSON. Try again."}, 500

    return {"text": raw}


@admin_bp.route("/chapter-topics/<int:ct_id>/delete", methods=["POST"])
@admin_required
def chapter_topic_delete(ct_id):
    ct = ChapterTopic.query.get_or_404(ct_id)
    location_id = ct.chapter.location_id
    db.session.delete(ct)
    db.session.commit()
    flash("Topic removed.", "success")
    return redirect(url_for("admin.edit_location", location_id=location_id))


@admin_bp.route("/visibility")
@admin_required
def visibility():
    locations = Location.query.order_by(Location.name).all()
    routes = Route.query.order_by(Route.name).all()
    return render_template("admin/visibility.html", locations=locations, routes=routes)


@admin_bp.route("/location/<location_id>/toggle-hidden", methods=["POST"])
@admin_required
def toggle_location_hidden(location_id):
    loc = Location.query.get_or_404(location_id)
    loc.hidden = not loc.hidden
    db.session.commit()
    return {"ok": True, "hidden": loc.hidden}


@admin_bp.route("/route/<route_id>/toggle-hidden", methods=["POST"])
@admin_required
def toggle_route_hidden(route_id):
    route = Route.query.get_or_404(route_id)
    route.hidden = not route.hidden
    db.session.commit()
    return {"ok": True, "hidden": route.hidden}


@admin_bp.route("/location/<location_id>/images/reorder", methods=["POST"])
@admin_required
def location_images_reorder(location_id):
    """Accept {image_ids: [id, id, ...]} and write sort_order 0,1,2,..."""
    Location.query.get_or_404(location_id)
    data = request.get_json() or {}
    image_ids = data.get("image_ids", [])
    for idx, image_id in enumerate(image_ids):
        link = LocationImage.query.filter_by(
            location_id=location_id, image_id=image_id
        ).first()
        if link:
            link.sort_order = idx
    db.session.commit()
    return {"ok": True}


@admin_bp.route("/location/<location_id>/images/sort-by-date", methods=["POST"])
@admin_required
def location_images_sort_by_date(location_id):
    """Keep sort_order=0 image as default; sort the rest by year ascending."""
    import re as _re
    links = (
        LocationImage.query
        .options(joinedload(LocationImage.image))
        .filter_by(location_id=location_id)
        .all()
    )
    if not links:
        return {"ok": True}

    # Separate default (sort_order == 0 or lowest) from the rest
    links.sort(key=lambda l: l.sort_order or 0)
    default_link = links[0]
    rest = links[1:]

    def year_key(link):
        match = _re.search(r'\d{4}', link.image.date or '')
        return int(match.group()) if match else 9999

    rest.sort(key=year_key)

    default_link.sort_order = 0
    for idx, link in enumerate(rest, start=1):
        link.sort_order = idx
    db.session.commit()
    return {"ok": True}


@admin_bp.route("/location/<location_id>/images/<image_id>/detach", methods=["POST"])
@admin_required
def location_image_detach(location_id, image_id):
    link = LocationImage.query.filter_by(location_id=location_id, image_id=image_id).first_or_404()
    db.session.delete(link)
    db.session.commit()
    flash("Photo removed from location.", "success")
    return redirect(url_for("admin.edit_location", location_id=location_id))