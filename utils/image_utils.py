import os, json, hashlib
from PIL import Image, ImageOps, ExifTags
from datetime import datetime

def ensure_dirs(*paths):
    for p in paths:
        os.makedirs(p, exist_ok=True)

def hash_name(original: str) -> str:
    stem, ext = os.path.splitext(original)
    h = hashlib.sha1((original + str(datetime.utcnow())).encode()).hexdigest()[:12]
    return f"{stem}-{h}{ext.lower()}".replace(" ", "_")

def extract_exif_as_json(img: Image.Image) -> str:
    try:
        raw = img.getexif()
        mapped = {}
        for k, v in raw.items():
            tag = ExifTags.TAGS.get(k, str(k))
            if isinstance(v, bytes):
                # keep small bytes only
                v = v[:40].hex()
            mapped[tag] = v
        return json.dumps(mapped)
    except Exception:
        return "{}"

def letterbox_to(image: Image.Image, target_w: int, target_h: int) -> Image.Image:
    # preserves aspect ratio, pads with black
    return ImageOps.pad(image, (target_w, target_h), color="black", method=Image.Resampling.LANCZOS)

def crop_and_fill(image: Image.Image, target_w: int, target_h: int, crop_x: int = 0, crop_y: int = 0, crop_width: int = 100, crop_height: int = 100) -> Image.Image:
    """
    Crop a region from the image and fill the target dimensions
    crop_x, crop_y, crop_width, crop_height are percentages (0-100)
    """
    orig_w, orig_h = image.size
    
    # Convert percentages to pixels
    left = int(orig_w * crop_x / 100)
    top = int(orig_h * crop_y / 100)
    width = int(orig_w * crop_width / 100)
    height = int(orig_h * crop_height / 100)
    
    # Ensure crop dimensions don't exceed image boundaries
    left = max(0, min(left, orig_w - 1))
    top = max(0, min(top, orig_h - 1))
    right = min(orig_w, left + width)
    bottom = min(orig_h, top + height)
    
    # Crop the image
    cropped = image.crop((left, top, right, bottom))
    
    # Resize to fill target dimensions (may stretch slightly)
    return cropped.resize((target_w, target_h), Image.Resampling.LANCZOS)

def save_upload(fileobj, upload_dir: str, thumb_dir: str) -> tuple[str, int, int, str]:
    ensure_dirs(upload_dir, thumb_dir)
    original_name = getattr(fileobj, "filename", "upload")
    safe_name = hash_name(os.path.basename(original_name))
    dest_path = os.path.join(upload_dir, safe_name)
    with open(dest_path, "wb") as out:
        out.write(fileobj.file.read())

    img = Image.open(dest_path).convert("RGB")
    w, h = img.size
    exif_json = extract_exif_as_json(img)

    # thumbnail (max 480px on long side)
    t = img.copy()
    t.thumbnail((480, 480))
    t.save(os.path.join(thumb_dir, safe_name), "JPEG", quality=85)

    return safe_name, w, h, exif_json

def render_to_output(src_path: str, output_path: str, resolution: str, crop_x: int = 0, crop_y: int = 0, crop_width: int = 100, crop_height: int = 100, preserve_aspect_ratio: bool = False):
    w, h = [int(x) for x in resolution.split(",")]
    img = Image.open(src_path).convert("RGB")
    
    if preserve_aspect_ratio:
        # Use letterboxing to preserve original aspect ratio
        framed = letterbox_to(img, w, h)
    else:
        # Use crop-and-fill for full coverage
        framed = crop_and_fill(img, w, h, crop_x, crop_y, crop_width, crop_height)
    
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    framed.save(output_path, "JPEG", quality=90)
