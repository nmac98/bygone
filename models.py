from extensions import db
from datetime import datetime, timezone
import enum

def utcnow():
    return datetime.now(timezone.utc)

class LocationCategory(enum.Enum):
    LANDMARK = "LANDMARK"
    POI = "POI"
    PUB = "PUB"
    COFFEE = "COFFEE"

class Location(db.Model):
    __tablename__ = "location"

    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    lat = db.Column(db.Float, nullable=True)
    lon = db.Column(db.Float, nullable=True)
    description = db.Column(db.Text, nullable=True)
    themes = db.Column(db.JSON, nullable=True)

    chapters = db.relationship(
        "LocationChapter",
        back_populates="location",
        cascade="all, delete-orphan",
        order_by="LocationChapter.sort_order.asc()",
    )

    category = db.Column(db.Enum(LocationCategory, name="locationcategory"), nullable=False, server_default=LocationCategory.POI.value)

    @property
    def supabase_image_assets(self):
        rows = sorted(self.supabase_images, key=lambda r: r.sort_order or 0)
        return [r.image for r in rows]

class Route(db.Model):
    __tablename__ = "route"

    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    cover_image = db.Column(db.String(500), nullable=True)

    stops = db.relationship('RouteStop', backref='route', lazy=True, order_by="RouteStop.order", cascade="all, delete-orphan")

class RouteStop(db.Model):
    __tablename__ = "route_stop"

    id = db.Column(db.Integer, primary_key=True)
    order = db.Column(db.Integer, nullable=False)
    dialogue = db.Column(db.Text, nullable=True)
    route_id = db.Column(db.String, db.ForeignKey('route.id'), nullable=False)
    location_id = db.Column(db.String, db.ForeignKey('location.id'), nullable=False)
    location = db.relationship('Location')

class ImageAsset(db.Model):
    __tablename__ = "images"
    id = db.Column(db.String(26), primary_key=True)  # ULID
    title = db.Column(db.String(200), nullable=True)
    date = db.Column(db.String(30), nullable=True)
    description = db.Column(db.Text, nullable=True)
    lat = db.Column(db.Float, nullable=True)
    lon = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

class ImageFile(db.Model):
    __tablename__ = "image_files"
    id = db.Column(db.Integer, primary_key=True)
    image_id = db.Column(db.String(26), db.ForeignKey("images.id"), nullable=False)
    variant = db.Column(db.String(50), default="original", nullable=False)  # keep minimal
    bucket = db.Column(db.String(100), nullable=False)
    storage_key = db.Column(db.String(500), nullable=False)
    public_url = db.Column(db.String(1000), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    image = db.relationship("ImageAsset", backref=db.backref("files", lazy=True, cascade="all, delete-orphan"))

class LocationImage(db.Model):
    __tablename__ = "location_images"
    location_id = db.Column(db.String, db.ForeignKey("location.id"), primary_key=True)
    image_id = db.Column(db.String(26), db.ForeignKey("images.id"), primary_key=True)
    sort_order = db.Column(db.Integer, default=0)

    location = db.relationship("Location", backref=db.backref("supabase_images", lazy=True, cascade="all, delete-orphan"))
    image = db.relationship("ImageAsset", backref=db.backref("locations", lazy=True, cascade="all, delete-orphan"))

class LocationChapter(db.Model):
    __tablename__ = "location_chapter"

    id = db.Column(db.Integer, primary_key=True)
    location_id = db.Column(db.String, db.ForeignKey("location.id"), nullable=False)

    title = db.Column(db.String(200), nullable=False)
    summary = db.Column(db.Text, nullable=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    location = db.relationship("Location", back_populates="chapters")
    blocks = db.relationship(
        "ChapterBlock",
        back_populates="chapter",
        cascade="all, delete-orphan",
        order_by="ChapterBlock.sort_order.asc()",
    )

    chapter_topics = db.relationship(
        "ChapterTopic",
        back_populates="chapter",
        cascade="all, delete-orphan",
        order_by="ChapterTopic.sort_order.asc()",
    )

class ChapterBlock(db.Model):
    """
    Flexible ordered content inside a chapter.
    block_type: text | image | link | divider
    """
    __tablename__ = "chapter_block"

    id = db.Column(db.Integer, primary_key=True)
    chapter_id = db.Column(db.Integer, db.ForeignKey("location_chapter.id"), nullable=False)

    block_type = db.Column(db.String(30), nullable=False)  # "text", "image", "link", "divider"
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    # text
    body = db.Column(db.Text, nullable=True)

    # image (store a reference to your existing image/asset table)
    # IMPORTANT: change "image_asset" to whatever your actual image model table is.
    image_asset_id = db.Column(db.String(26), db.ForeignKey("images.id"), nullable=True)
    caption_override = db.Column(db.String(255), nullable=True)

    # link
    link_label = db.Column(db.String(255), nullable=True)
    link_url = db.Column(db.String(1000), nullable=True)
    link_note = db.Column(db.String(500), nullable=True)

    chapter = db.relationship("LocationChapter", back_populates="blocks")
    image_asset = db.relationship("ImageAsset")  # rename to your actual model


class Topic(db.Model):
    __tablename__ = "topic"

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(200), unique=True, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    summary = db.Column(db.Text, nullable=True)
    default_url = db.Column(db.String(1000), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    chapter_topics = db.relationship("ChapterTopic", back_populates="topic", cascade="all, delete-orphan")


class ChapterTopic(db.Model):
    """
    Join table: attach reusable Topics to chapters, with ordering + optional per-chapter label/note.
    """
    __tablename__ = "chapter_topic"

    id = db.Column(db.Integer, primary_key=True)
    chapter_id = db.Column(db.Integer, db.ForeignKey("location_chapter.id"), nullable=False)
    topic_id = db.Column(db.Integer, db.ForeignKey("topic.id"), nullable=False)

    sort_order = db.Column(db.Integer, nullable=False, default=0)
    label_override = db.Column(db.String(255), nullable=True)
    note = db.Column(db.String(500), nullable=True)

    chapter = db.relationship("LocationChapter", back_populates="chapter_topics")
    topic = db.relationship("Topic", back_populates="chapter_topics")

    __table_args__ = (
        db.UniqueConstraint("chapter_id", "topic_id", name="uq_chapter_topic_once"),
    )
