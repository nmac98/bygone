from flask import render_template, abort, request
from . import locations_bp
from models import (
    Location, Route,
    LocationImage, ImageAsset,
    LocationChapter, ChapterBlock, ChapterTopic
)
from sqlalchemy.orm import joinedload


@locations_bp.route("/gallery/<loc_id>")
def gallery(loc_id):

    # === CHAPTERS FEATURE: CHANGED ===
    # Eager-load:
    # - location.supabase_images -> image -> files (carousel)
    # - location.chapters -> blocks -> image_asset -> files (chapter images)
    # - location.chapters -> chapter_topics -> topic (find out more)
    loc = (
        Location.query
        .options(
            # Existing: carousel images
            joinedload(Location.supabase_images)
                .joinedload(LocationImage.image)
                .joinedload(ImageAsset.files),

            # New: chapters + blocks + image assets
            joinedload(Location.chapters)
                .joinedload(LocationChapter.blocks)
                .joinedload(ChapterBlock.image_asset)
                .joinedload(ImageAsset.files),

            # New: chapters + attached topics
            joinedload(Location.chapters)
                .joinedload(LocationChapter.chapter_topics)
                .joinedload(ChapterTopic.topic),
        )
        .get(loc_id)
    )

    if not loc:
        abort(404, description="Location not found")

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
        # === CHAPTERS FEATURE: CHANGED (perf only) ===
        # Eager-load stops + their locations to avoid extra queries
        route = (
            Route.query
            .options(joinedload(Route.stops).joinedload("location"))
            .get(route_id)
        )

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
