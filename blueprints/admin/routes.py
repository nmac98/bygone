from flask import render_template, request, url_for, redirect, current_app, flash
from utils.decorators import admin_required
from . import admin_bp
from models import Location, Image, Route, RouteStop
from extensions import db

import os

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

@admin_bp.route('/photos')
@admin_required
def admin_photos():
    images = Image.query.order_by(Image.id.desc()).all()
    return render_template('admin/photos_list.html', images=images)


@admin_bp.route('/photo/upload', methods=['GET', 'POST'])
@admin_required
def upload_photo():
    locations = Location.query.order_by(Location.name).all()

    if request.method == 'POST':
        file = request.files.get('file')

        if not file or file.filename == '':
            flash('No file selected.', 'error')
            return redirect(request.url)

        if not allowed_file(file.filename):
            flash('Invalid file type. Please upload an image.', 'error')
            return redirect(request.url)

        filename = secure_filename(file.filename)

        # Save to static/images
        images_folder = os.path.join(current_app.root_path, 'static', 'images')
        os.makedirs(images_folder, exist_ok=True)

        save_path = os.path.join(images_folder, filename)

        # If file exists, tweak filename
        original_filename = filename
        counter = 1
        while os.path.exists(save_path):
            name, ext = os.path.splitext(original_filename)
            filename = f"{name}_{counter}{ext}"
            save_path = os.path.join(images_folder, filename)
            counter += 1

        file.save(save_path)

        # Create Image record
        title = request.form.get('title') or ''
        date = request.form.get('date') or ''
        description = request.form.get('description') or ''
        location_id = request.form.get('location_id') or None

        # Optional lat/lon + show_on_map
        lat_raw = request.form.get('lat') or None
        lon_raw = request.form.get('lon') or None
        show_on_map = bool(request.form.get('show_on_map'))

        lat = float(lat_raw) if lat_raw else None
        lon = float(lon_raw) if lon_raw else None

        new_image = Image(
            file=filename,
            title=title,
            date=date,
            description=description,
            location_id=location_id,
            lat=lat,
            lon=lon,
            show_on_map=show_on_map
        )

        db.session.add(new_image)
        db.session.commit()

        flash('Image uploaded successfully.', 'success')
        return redirect(url_for('admin.admin_photos'))

    return render_template('admin/photo_upload.html', locations=locations)


@admin_bp.route('/photo/<int:image_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_photo(image_id):
    image = Image.query.get_or_404(image_id)
    locations = Location.query.order_by(Location.name).all()

    if request.method == 'POST':
        image.title = request.form.get('title') or ''
        image.date = request.form.get('date') or ''
        image.description = request.form.get('description') or ''
        image.location_id = request.form.get('location_id') or None

        lat_raw = request.form.get('lat') or None
        lon_raw = request.form.get('lon') or None
        image.lat = float(lat_raw) if lat_raw else None
        image.lon = float(lon_raw) if lon_raw else None

        image.show_on_map = bool(request.form.get('show_on_map'))

        db.session.commit()
        flash('Image updated successfully.', 'success')
        return redirect(url_for('admin.admin_photos'))

    return render_template('admin/photo_edit.html', image=image, locations=locations)


@admin_bp.route('/photo/<int:image_id>/delete', methods=['GET', 'POST'])
@admin_required
def delete_photo(image_id):
    image = Image.query.get_or_404(image_id)

    if request.method == 'POST':
        # Delete file from disk (optional but nice)
        images_folder = os.path.join(current_app.root_path, 'static', 'images')
        file_path = os.path.join(images_folder, image.file)
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except OSError:
                # Don't crash if deletion fails
                pass

        db.session.delete(image)
        db.session.commit()
        flash('Image deleted.', 'success')
        return redirect(url_for('admin.admin_photos'))

    return render_template('admin/photo_delete.html', image=image)

@admin_bp.route('/routes')
@admin_required
def admin_routes():
    routes = Route.query.order_by(Route.name).all()
    return render_template('admin/routes_list.html', routes=routes)

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
