from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Settings(Base):
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True)
    image_root = Column(String, default="static/uploads")
    thumb_root = Column(String, default="static/thumbs")
    resolution = Column(String, default="800,480")
    interval_ms = Column(Integer, default=600000)
    order_mode = Column(String, default="added")  # added|random|custom
    slideshow_enabled = Column(Boolean, default=True)

class Image(Base):
    __tablename__ = "images"
    id = Column(Integer, primary_key=True)
    filename = Column(String, unique=True, nullable=False)   # stored basename
    original_name = Column(String)
    title = Column(String, default="")
    description = Column(Text, default="")
    exif_json = Column(Text, default="{}")
    width = Column(Integer, default=0)
    height = Column(Integer, default=0)
    enabled = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)
    times_shown = Column(Integer, default=0)
    last_shown_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())
    # Crop settings as percentages (0-100) of original image
    crop_x = Column(Float, default=0.0)  # left offset %
    crop_y = Column(Float, default=0.0)  # top offset %
    crop_width = Column(Float, default=100.0)  # width %
    crop_height = Column(Float, default=100.0)  # height %
    # Aspect ratio preservation option
    preserve_aspect_ratio = Column(Boolean, default=False)  # True = letterbox, False = crop-to-fill
