import os, random, threading, time
from fastapi import FastAPI, Request, UploadFile, File, Form, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import SessionLocal, init_db
from models import Settings, Image
from utils import eframe_inky
from utils.image_utils import save_upload, render_to_output, ensure_dirs

app = FastAPI()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

SLIDESHOW_THREAD = {"t": None, "stop": False}

@app.on_event("startup")
def startup():
    init_db()
    with SessionLocal() as db:
        s = db.query(Settings).first()
        if not s:
            s = Settings()
            db.add(s); db.commit()
        ensure_dirs(s.image_root, s.thumb_root, os.path.dirname("static/current.jpg"))
    # kick slideshow thread
    start_slideshow()

@app.get("/", name="home")
def index(request: Request, db: Session = Depends(get_db)):
    imgs = db.query(Image).order_by(Image.sort_order.asc(), Image.created_at.asc()).all()
    settings = db.query(Settings).first()
    return templates.TemplateResponse("index.html", {"request": request, "images": imgs, "settings": settings})

@app.get("/upload", name="upload")
def upload_form(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})

@app.post("/upload")
def upload(file: UploadFile = File(...),
           title: str = Form(""),
           description: str = Form(""),
           db: Session = Depends(get_db)):
    s = db.query(Settings).first()
    fname, w, h, exif_json = save_upload(file, s.image_root, s.thumb_root)
    # sort_order = max + 1
    max_order = db.query(Image).count()
    img = Image(filename=fname, original_name=file.filename, title=title,
                description=description, exif_json=exif_json,
                width=w, height=h, sort_order=max_order+1)
    db.add(img); db.commit()
    return RedirectResponse("/", status_code=303)

@app.post("/image/{id}/toggle")
def toggle_enable(id: int, db: Session = Depends(get_db)):
    img = db.query(Image).get(id)
    if not img: return JSONResponse({"error":"not found"}, status_code=404)
    img.enabled = not img.enabled
    db.commit()
    return {"enabled": img.enabled}

@app.post("/image/{id}/update")
def update_image(id: int,
                 title: str = Form(""),
                 description: str = Form(""),
                 sort_order: int = Form(None),
                 db: Session = Depends(get_db)):
    img = db.query(Image).get(id)
    if not img: return JSONResponse({"error":"not found"}, status_code=404)
    img.title = title; img.description = description
    if sort_order is not None: img.sort_order = sort_order
    db.commit(); return {"ok": True}

@app.post("/image/{id}/delete")
def delete_image(id: int, db: Session = Depends(get_db)):
    s = db.query(Settings).first()
    img = db.query(Image).get(id)
    if not img: return JSONResponse({"error":"not found"}, status_code=404)
    # remove files
    for root in (s.image_root, s.thumb_root):
        p = os.path.join(root, img.filename)
        if os.path.exists(p): os.remove(p)
    db.delete(img); db.commit()
    return {"ok": True}

@app.get("/settings")
def settings_page(request: Request, db: Session = Depends(get_db)):
    s = db.query(Settings).first()
    if not s:
        raise HTTPException(500, "Settings row missing")
    return templates.TemplateResponse("settings.html", {"request": request, "settings": s})

# app.py – REPLACE the existing /settings handler with this:
@app.post("/settings", name="settings")
def update_settings(
    interval_ms: int = Form(...),
    order_mode: str = Form(...),
    slideshow_enabled: int = Form(...),
    image_root: str = Form(...),
    thumb_root: str = Form(...),
    resolution: str = Form(...),  # e.g. "800,480"
    db: Session = Depends(get_db)
):
    s = db.query(Settings).first()
    s.interval_ms = interval_ms
    s.order_mode = order_mode
    s.slideshow_enabled = bool(slideshow_enabled)
    s.image_root = image_root.strip()
    s.thumb_root = thumb_root.strip()
    s.resolution = resolution.strip()

    # Make sure folders exist after edits
    ensure_dirs(s.image_root, s.thumb_root, os.path.dirname("static/current.jpg"))

    db.commit()
    return RedirectResponse("/settings", status_code=303)

@app.post("/show-now/{id}")
def show_now(id: int, db: Session = Depends(get_db)):
    s = db.query(Settings).first()
    img = db.query(Image).get(id)
    if not img: return JSONResponse({"error":"not found"}, status_code=404)
    src = os.path.join(s.image_root, img.filename)
    render_to_output(src, "static/current.jpg", s.resolution)
    eframe_inky.show_on_inky("static/current.jpg")
    img.times_shown += 1
    db.commit()
    return {"ok": True}

def pick_next(db: Session, s: Settings) -> Image | None:
    q = db.query(Image).filter(Image.enabled == True)
    if s.order_mode == "random":
        imgs = q.all()
        return random.choice(imgs) if imgs else None
    # added/custom: order by sort_order then created_at
    return q.order_by(Image.sort_order.asc(), Image.created_at.asc()).first()

def slideshow_loop():
    while not SLIDESHOW_THREAD["stop"]:
        interval_seconds = 600  # default fallback
        try:
            with SessionLocal() as db:
                s = db.query(Settings).first()
                if s:
                    # compute the sleep interval while session is open
                    interval_seconds = max(5, int(s.interval_ms) / 1000)
                if s and s.slideshow_enabled:
                    img = pick_next(db, s)
                    if img:
                        render_to_output(os.path.join(s.image_root, img.filename),
                                         "static/current.jpg", s.resolution)
                        eframe_inky.show_on_inky("static/current.jpg")
                        img.times_shown += 1
                        img.last_shown_at = None  # set timestamp if you want
                        db.commit()
        except Exception as e:
            print("Slideshow error:", e)
            interval_seconds = 10  # back off briefly on error

        time.sleep(interval_seconds)


def start_slideshow():
    if SLIDESHOW_THREAD["t"] and SLIDESHOW_THREAD["t"].is_alive():
        return
    SLIDESHOW_THREAD["stop"] = False
    SLIDESHOW_THREAD["t"] = threading.Thread(target=slideshow_loop, daemon=True)
    SLIDESHOW_THREAD["t"].start()

if __name__ == "__main__":
    import uvicorn
    import socket

    # Get local IP address
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = "127.0.0.1"

    print(f"INFO:     Local machine IP address: http://{local_ip}:8080")

    uvicorn.run(app, host="0.0.0.0", port=8080)

