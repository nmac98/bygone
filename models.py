from extensions import db
from flask_login import UserMixin
from datetime import datetime, timezone

class Location(db.Model):
    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String(200))
    lat = db.Column(db.Float)
    lon = db.Column(db.Float)
    description = db.Column(db.Text)
    themes = db.Column(db.JSON)

    images = db.relationship('Image', backref='location', lazy=True)

    @property
    def supabase_image_assets(self):
        rows = sorted(self.supabase_images, key=lambda r: r.sort_order or 0)
        return [r.image for r in rows]

class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file = db.Column(db.String(200))
    title = db.Column(db.String(200))
    date = db.Column(db.String(20))
    description = db.Column(db.Text)
    lat = db.Column(db.Float, nullable=True)
    lon = db.Column(db.Float, nullable=True)
    show_on_map = db.Column(db.Boolean, default=False)
    
    location_id = db.Column(db.String, db.ForeignKey('location.id'))

class Route(db.Model):
    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String(200))
    description = db.Column(db.Text)

    stops = db.relationship('RouteStop', backref='route', lazy=True, order_by="RouteStop.order")

class RouteStop(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order = db.Column(db.Integer)
    dialogue = db.Column(db.Text)
    route_id = db.Column(db.String, db.ForeignKey('route.id'))
    location_id = db.Column(db.String, db.ForeignKey('location.id'))
    location = db.relationship('Location')

class ImageAsset(db.Model):
    __tablename__ = "images"
    id = db.Column(db.String(26), primary_key=True)  # ULID
    title = db.Column(db.String(200), nullable=True)
    date = db.Column(db.String(30), nullable=True)
    description = db.Column(db.Text, nullable=True)
    lat = db.Column(db.Float, nullable=True)
    lon = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

class ImageFile(db.Model):
    __tablename__ = "image_files"
    id = db.Column(db.Integer, primary_key=True)
    image_id = db.Column(db.String(26), db.ForeignKey("images.id"), nullable=False)
    variant = db.Column(db.String(50), default="original", nullable=False)  # keep minimal
    bucket = db.Column(db.String(100), nullable=False)
    storage_key = db.Column(db.String(500), nullable=False)
    public_url = db.Column(db.String(1000), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc))

    image = db.relationship("ImageAsset", backref=db.backref("files", lazy=True, cascade="all, delete-orphan"))

class LocationImage(db.Model):
    __tablename__ = "location_images"
    location_id = db.Column(db.String, db.ForeignKey("location.id"), primary_key=True)
    image_id = db.Column(db.String(26), db.ForeignKey("images.id"), primary_key=True)
    sort_order = db.Column(db.Integer, default=0)

    location = db.relationship("Location", backref=db.backref("supabase_images", lazy=True, cascade="all, delete-orphan"))
    image = db.relationship("ImageAsset", backref=db.backref("locations", lazy=True, cascade="all, delete-orphan"))
