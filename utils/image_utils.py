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

def render_to_output(src_path: str, output_path: str, resolution: str):
    w, h = [int(x) for x in resolution.split(",")]
    img = Image.open(src_path).convert("RGB")
    framed = letterbox_to(img, w, h)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    framed.save(output_path, "JPEG", quality=90)
