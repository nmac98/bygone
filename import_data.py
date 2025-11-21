import json
from app import app
from extensions import db
from models import Location, Image, Route, RouteStop

def load_locations():
    with open("data/locations.json") as f:
        locations = json.load(f)

    for loc in locations:
        location = Location(
            id=loc["id"],
            name=loc["name"],
            lat=loc["lat"],
            lon=loc["lon"],
            description=loc["description"],
            themes=loc.get("themes", [])
        )
        db.session.add(location)

        # add images
        for img in loc.get("images", []):
            image = Image(
                file=img["file"],
                title=img["title"],
                date=img["date"],
                description=img["description"],
                location=location
            )
            db.session.add(image)

    db.session.commit()


def load_routes():
    try:
        with open("data/routes.json") as f:
            routes = json.load(f)

        for r in routes:
            route = Route(
                id=r["id"],
                name=r["name"],
                description=r["description"]
            )
            db.session.add(route)

            for index, stop in enumerate(r["stops"]):
                route_stop = RouteStop(
                    order=index,
                    dialogue=stop["dialogue"],
                    route=route,
                    location_id=stop["location_id"]
                )
                db.session.add(route_stop)

        db.session.commit()
        print("Routes loaded successfully." )
    
    except Exception as e:
        db.session.rollback()
        print(f"Error loading routes: {e}")
        raise e



if __name__ == "__main__":
    with app.app_context():
        load_locations()
        load_routes()
        print("Data imported successfully!")
