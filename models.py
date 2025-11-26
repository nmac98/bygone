from extensions import db
from flask_login import UserMixin

class Location(db.Model):
    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String(200))
    lat = db.Column(db.Float)
    lon = db.Column(db.Float)
    description = db.Column(db.Text)
    themes = db.Column(db.JSON)

    images = db.relationship('Image', backref='location', lazy=True)

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
