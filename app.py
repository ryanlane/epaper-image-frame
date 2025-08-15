import os, random, threading, time, queue, uuid, hashlib
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
import os, random, threading, time, queue, uuid, hashlib
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

from fastapi import FastAPI, Request, UploadFile, File, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import case
from dotenv import load_dotenv
from database import SessionLocal, init_db
from models import Settings, Image
from utils import eframe_inky
from utils.image_utils import save_upload, render_to_output, ensure_dirs

# Load environment variables from .env file
load_dotenv()

def is_dev_mode():
    """Check if application is running in development mode based on environment variable"""
    env = os.getenv('ENVIRONMENT', '').lower()
    return env in ('development', 'dev')

def calculate_smart_crop(image_width, image_height, display_resolution):
    """
    Calculate smart default crop that centers the image if it needs cropping.
    Returns (crop_x, crop_y, crop_width, crop_height) as percentages.
    """
    if not display_resolution or ',' not in display_resolution:
        # Fallback to full image if no valid resolution
        return 0, 0, 100, 100
    
    try:
        display_width, display_height = map(int, display_resolution.split(','))
        display_aspect = display_width / display_height
        image_aspect = image_width / image_height
        
        if abs(display_aspect - image_aspect) < 0.01:
            # Aspect ratios are very close, use full image
            return 0, 0, 100, 100
        
        if image_aspect > display_aspect:
            # Image is wider than display - crop horizontally, center left-right
            crop_height = 100  # Use full height
            crop_width = (display_aspect / image_aspect) * 100
            crop_x = (100 - crop_width) / 2  # Center horizontally
            crop_y = 0
        else:
            # Image is taller than display - crop vertically, center top-bottom  
            crop_width = 100  # Use full width
            crop_height = (image_aspect / display_aspect) * 100
            crop_x = 0
            crop_y = (100 - crop_height) / 2  # Center vertically
        
        # Round to 2 decimal places
        return round(crop_x, 2), round(crop_y, 2), round(crop_width, 2), round(crop_height, 2)
        
    except (ValueError, ZeroDivisionError):
        # Fallback to full image on any calculation error
        return 0, 0, 100, 100

@asynccontextmanager
async def lifespan(app: FastAPI):

    # Startup
    init_db()
    with SessionLocal() as db:
        s = db.query(Settings).first()
        if not s:
            s = Settings()
            # Try to set resolution to Inky display resolution if available
            try:
                from utils.eframe_inky import inky
                if inky and hasattr(inky, "resolution"):
                    res = inky.resolution
                    s.resolution = f"{res[0]},{res[1]}"
            except Exception:
                pass
            db.add(s); db.commit()
        ensure_dirs(s.image_root, s.thumb_root, os.path.dirname("static/current.jpg"))
    
    # Start background threads
    start_display_worker()
    start_upload_worker()
    start_slideshow()
    
    yield
    
    # Shutdown
    print("[SHUTDOWN] Stopping background threads...")
    stop_display_worker()
    stop_upload_worker()
    SLIDESHOW_THREAD["stop"] = True
    if SLIDESHOW_THREAD["t"] and SLIDESHOW_THREAD["t"].is_alive():
        SLIDESHOW_THREAD["t"].join(timeout=5)

app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

def get_db():
    db = SessionLocal()
    try: yield db
    finally: db.close()

# Global display queue and thread management
DISPLAY_QUEUE = queue.Queue()
DISPLAY_THREAD = {"t": None, "stop": False}
SLIDESHOW_THREAD = {"t": None, "stop": False}

# Global upload queue and status tracking
UPLOAD_QUEUE = queue.Queue()
UPLOAD_STATUS: Dict[str, Any] = {}  # task_id -> status info
UPLOAD_THREAD = {"t": None, "stop": False}

def display_worker():
    """Worker thread that processes display queue in background"""
    while not DISPLAY_THREAD["stop"]:
        try:
            # Wait for display request with timeout
            display_request = DISPLAY_QUEUE.get(timeout=1)
            if display_request is None:  # Shutdown signal
                break
                
            image_path, image_id = display_request
            print(f"[DISPLAY] Processing: {image_path}")
            
            # This is the potentially slow operation
            eframe_inky.show_on_inky(image_path)
            
            # Update database stats in background
            if image_id:
                try:
                    with SessionLocal() as db:
                        img = db.get(Image, image_id)
                        if img:
                            img.times_shown += 1
                            img.last_shown_at = datetime.now(timezone.utc)
                            db.commit()
                except Exception as e:
                    print(f"Error updating display stats: {e}")
                    
            DISPLAY_QUEUE.task_done()
            
        except queue.Empty:
            continue  # Check stop flag and try again
        except Exception as e:
            print(f"Display worker error: {e}")

def queue_display(image_path, image_id=None):
    """Queue an image for display on the e-ink screen"""
    try:
        DISPLAY_QUEUE.put((image_path, image_id), block=False)
        print(f"[DISPLAY] Queued: {image_path}")
        return True
    except queue.Full:
        print("[DISPLAY] Warning: Display queue is full, skipping")
        return False

def start_display_worker():
    """Start the background display worker thread"""
    if DISPLAY_THREAD["t"] is None or not DISPLAY_THREAD["t"].is_alive():
        DISPLAY_THREAD["stop"] = False
        DISPLAY_THREAD["t"] = threading.Thread(target=display_worker, daemon=True)
        DISPLAY_THREAD["t"].start()
        print("[DISPLAY] Worker thread started")

def stop_display_worker():
    """Stop the background display worker thread"""
    DISPLAY_THREAD["stop"] = True
    DISPLAY_QUEUE.put(None)  # Signal shutdown
    if DISPLAY_THREAD["t"] and DISPLAY_THREAD["t"].is_alive():
        DISPLAY_THREAD["t"].join(timeout=5)
        print("[DISPLAY] Worker thread stopped")

def upload_worker():
    """Worker thread that processes upload queue in background"""
    worker_id = threading.current_thread().ident
    print(f"[UPLOAD] Worker {worker_id} started")
    
    while not UPLOAD_THREAD["stop"]:
        try:
            upload_task = UPLOAD_QUEUE.get(timeout=1)
            if upload_task is None:  # Shutdown signal
                break
                
            task_id, files_data, title, description = upload_task
            print(f"[UPLOAD] Worker {worker_id} processing task {task_id} with {len(files_data)} files")
            
            # Check if this task is already being processed
            if task_id in UPLOAD_STATUS and UPLOAD_STATUS[task_id]["status"] == "processing":
                print(f"[UPLOAD] ERROR: Task {task_id} is already being processed! Skipping duplicate.")
                UPLOAD_QUEUE.task_done()
                continue
            
            # Update status
            UPLOAD_STATUS[task_id] = {
                "status": "processing", 
                "progress": 0, 
                "total": len(files_data),
                "uploaded": 0,
                "errors": [],
                "started_at": datetime.now(),
                "last_activity": datetime.now(),
                "current_file": None
            }
            
            # Get database session
            db = SessionLocal()
            try:
                s = db.query(Settings).first()
                uploaded_count = 0
                
                for i, (filename, file_content) in enumerate(files_data):
                    try:
                        # Update progress
                        UPLOAD_STATUS[task_id]["progress"] = i
                        UPLOAD_STATUS[task_id]["current_file"] = filename
                        UPLOAD_STATUS[task_id]["last_activity"] = datetime.now()
                        print(f"[UPLOAD] Processing {i+1}/{len(files_data)}: {filename} ({len(file_content)} bytes)")
                        
                        # Check for duplicate files in the current batch
                        duplicate_in_batch = sum(1 for f, _ in files_data if f == filename)
                        if duplicate_in_batch > 1:
                            print(f"[UPLOAD] WARNING: Found {duplicate_in_batch} instances of {filename} in current batch!")
                        
                        # Use filename as title if no default title provided
                        file_title = title if title.strip() else os.path.splitext(filename)[0]
                        
                        # Create a file-like object from bytes
                        from io import BytesIO
                        file_obj = type('UploadFile', (), {
                            'filename': filename,
                            'file': BytesIO(file_content)
                        })()
                        
                        print(f"[UPLOAD] Saving file: {filename} ({len(file_content)} bytes)")
                        UPLOAD_STATUS[task_id]["last_activity"] = datetime.now()
                        fname, w, h, exif_json = save_upload(file_obj, s.image_root, s.thumb_root)
                        print(f"[UPLOAD] File saved as: {fname} ({w}x{h})")
                        
                        # Check if this filename already exists in database
                        existing_img = db.query(Image).filter(Image.filename == fname).first()
                        if existing_img:
                            print(f"[UPLOAD] WARNING: File {fname} already exists in database, skipping")
                            continue
                        
                        # Calculate smart default crop
                        UPLOAD_STATUS[task_id]["last_activity"] = datetime.now()
                        crop_x, crop_y, crop_width, crop_height = calculate_smart_crop(w, h, s.resolution)
                        
                        # Add to database
                        UPLOAD_STATUS[task_id]["last_activity"] = datetime.now()
                        max_order = db.query(Image).count()
                        img = Image(filename=fname, original_name=filename, title=file_title,
                                    description=description, exif_json=exif_json,
                                    width=w, height=h, sort_order=max_order+1,
                                    crop_x=crop_x, crop_y=crop_y, 
                                    crop_width=crop_width, crop_height=crop_height)
                        db.add(img)
                        
                        # Flush to check for any database errors before continuing
                        try:
                            db.flush()
                            uploaded_count += 1
                            UPLOAD_STATUS[task_id]["uploaded"] = uploaded_count
                            UPLOAD_STATUS[task_id]["last_activity"] = datetime.now()
                            print(f"[UPLOAD] Successfully processed: {filename} (crop: {crop_x:.1f}%, {crop_y:.1f}%, {crop_width:.1f}%x{crop_height:.1f}%)")
                        except Exception as db_error:
                            print(f"[UPLOAD] Database error for {filename}: {db_error}")
                            db.rollback()
                            # Continue with next file
                            continue
                        
                    except Exception as e:
                        error_msg = f"Failed to upload {filename}: {str(e)}"
                        print(f"[UPLOAD] ERROR: {error_msg}")
                        import traceback
                        traceback.print_exc()
                        UPLOAD_STATUS[task_id]["errors"].append(error_msg)
                        continue
                
                db.commit()
                
                # Mark as completed
                UPLOAD_STATUS[task_id]["status"] = "completed"
                UPLOAD_STATUS[task_id]["progress"] = len(files_data)
                UPLOAD_STATUS[task_id]["current_file"] = None
                print(f"[UPLOAD] Task {task_id} completed: {uploaded_count} of {len(files_data)} images")
                
            except Exception as e:
                db.rollback()
                UPLOAD_STATUS[task_id]["status"] = "error"
                UPLOAD_STATUS[task_id]["errors"].append(f"Database error: {str(e)}")
                print(f"[UPLOAD] Task {task_id} failed: {e}")
                import traceback
                traceback.print_exc()
            finally:
                db.close()
                UPLOAD_QUEUE.task_done()
                
        except queue.Empty:
            continue  # Check stop flag and try again
        except Exception as e:
            print(f"Upload worker error: {e}")

def start_upload_worker():
    """Start the background upload worker thread"""
    print(f"[UPLOAD] start_upload_worker called. Current thread: {UPLOAD_THREAD['t']}")
    if UPLOAD_THREAD["t"] is None or not UPLOAD_THREAD["t"].is_alive():
        UPLOAD_THREAD["stop"] = False
        UPLOAD_THREAD["t"] = threading.Thread(target=upload_worker, daemon=True)
        UPLOAD_THREAD["t"].start()
        print(f"[UPLOAD] Worker thread started: {UPLOAD_THREAD['t'].ident}")
    else:
        print(f"[UPLOAD] Worker thread already running: {UPLOAD_THREAD['t'].ident}")

def stop_upload_worker():
    """Stop the background upload worker thread"""
    UPLOAD_THREAD["stop"] = True
    UPLOAD_QUEUE.put(None)  # Signal shutdown
    if UPLOAD_THREAD["t"] and UPLOAD_THREAD["t"].is_alive():
        UPLOAD_THREAD["t"].join(timeout=5)
        print("[UPLOAD] Worker thread stopped")

@app.get("/", name="home")
def index(request: Request, db: Session = Depends(get_db)):
    print(f"[INDEX] Index page requested at {datetime.now()}")
    print(f"[INDEX] Request method: {request.method}")
    print(f"[INDEX] Request headers: {dict(request.headers)}")
    
    imgs = db.query(Image).order_by(Image.sort_order.asc(), Image.created_at.asc()).all()
    settings = db.query(Settings).first()
    
    # Check if current.jpg file actually exists
    current_image_exists = os.path.exists("static/current.jpg")
    
    print(f"[INDEX] Found {len(imgs)} images, current_image_exists: {current_image_exists}")
    
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "images": imgs, 
        "settings": settings,
        "current_image_exists": current_image_exists,
        "dev_mode": is_dev_mode()
    })

@app.get("/frame", name="frame")
def frame_view(request: Request):
    """Frame view - shows just the current image, auto-refreshing for slideshow testing"""
    print(f"[FRAME] Frame view requested at {datetime.now()}")
    
    # Check if current.jpg file actually exists
    current_image_exists = os.path.exists("static/current.jpg")
    
    # Get timestamp for cache busting
    timestamp = int(datetime.now().timestamp() * 1000)
    
    print(f"[FRAME] current_image_exists: {current_image_exists}, timestamp: {timestamp}")
    
    return templates.TemplateResponse("frame.html", {
        "request": request,
        "current_image_exists": current_image_exists,
        "timestamp": timestamp,
        "dev_mode": is_dev_mode()
    })

@app.get("/upload", name="upload")
def upload_form(request: Request):
    return templates.TemplateResponse("upload.html", {
        "request": request,
        "dev_mode": is_dev_mode()
    })

@app.post("/upload")
async def upload(request: Request):
    print(f"[UPLOAD] Upload endpoint called at {datetime.now()}")
    
    # Log user agent for Safari detection
    user_agent = request.headers.get("user-agent", "")
    is_safari_ios = "iPhone" in user_agent or "iPad" in user_agent or "iPod" in user_agent
    print(f"[UPLOAD] User-Agent: {user_agent}")
    print(f"[UPLOAD] Safari iOS detected: {is_safari_ios}")
    
    try:
        form = await request.form()
        print(f"[UPLOAD] Form keys: {list(form.keys())}")
        
        # Get title and description
        title = form.get("title", "")
        description = form.get("description", "")
        print(f"[UPLOAD] Title: '{title}', Description: '{description}'")
        
        # Get files - FastAPI/Starlette handles multiple files from single input differently
        files = form.getlist("files")
        print(f"[UPLOAD] Received {len(files)} files")
        
        # Safari iOS specific validation
        if is_safari_ios and len(files) > 5:
            print(f"[UPLOAD] WARNING: Safari iOS uploading {len(files)} files - may be unstable")
        
        # Debug: Check for duplicate files in the form data
        file_names = [getattr(f, 'filename', 'no-name') for f in files if hasattr(f, 'filename')]
        print(f"[UPLOAD] File names: {file_names}")
        
    except Exception as e:
        print(f"[UPLOAD] Error reading form data: {e}")
        return JSONResponse({"error": f"Failed to read upload data: {str(e)}"}, status_code=400)
    
    # Count duplicates
    from collections import Counter
    name_counts = Counter(file_names)
    duplicates = {name: count for name, count in name_counts.items() if count > 1}
    if duplicates:
        print(f"[UPLOAD] WARNING: Duplicate filenames in form data: {duplicates}")
    
    if not files or not any(hasattr(f, 'filename') and f.filename for f in files):
        return JSONResponse({"error": "No valid files provided"}, status_code=400)
    
    # Generate unique task ID
    task_id = str(uuid.uuid4())
    
    # Read file contents into memory (since we can't pass file objects between threads)
    # Safari iOS specific: Add better error handling for file reading
    files_data = []
    failed_files = []
    
    for i, file in enumerate(files):
        if hasattr(file, 'filename') and file.filename:
            try:
                print(f"[UPLOAD] Reading file {i+1}/{len(files)}: {file.filename}")
                content = await file.read()
                
                if len(content) == 0:
                    print(f"[UPLOAD] WARNING: File {file.filename} is empty, skipping")
                    failed_files.append(f"{file.filename} (empty file)")
                    continue
                    
                files_data.append((file.filename, content))
                print(f"[UPLOAD] Successfully queued: {file.filename} ({len(content)} bytes)")
                
            except Exception as e:
                print(f"[UPLOAD] ERROR: Failed to read file {file.filename}: {e}")
                failed_files.append(f"{file.filename} (read error: {str(e)})")
                continue
    
    if not files_data:
        error_msg = "No files could be processed"
        if failed_files:
            error_msg += f". Failed files: {', '.join(failed_files)}"
        return JSONResponse({"error": error_msg}, status_code=400)
    
    if failed_files:
        print(f"[UPLOAD] WARNING: Some files failed to process: {failed_files}")
    
    print(f"[UPLOAD] Total files to queue: {len(files_data)} (failed: {len(failed_files)})")
    
    # Log file details for debugging
    file_hashes = {}
    for i, (filename, content) in enumerate(files_data):
        content_hash = hashlib.sha256(content).hexdigest()[:16]
        print(f"[UPLOAD] File {i+1}: {filename} ({len(content)} bytes, hash: {content_hash})")
        if content_hash in file_hashes:
            print(f"[UPLOAD] WARNING: Duplicate content detected! Same content as file {file_hashes[content_hash]}")
        else:
            file_hashes[content_hash] = filename
    
    # Queue the upload task
    UPLOAD_QUEUE.put((task_id, files_data, title, description))
    
    # Initialize status tracking
    UPLOAD_STATUS[task_id] = {
        "status": "queued", 
        "progress": 0, 
        "total": len(files_data),
        "uploaded": 0,
        "errors": []
    }
    
    print(f"Upload task {task_id} queued with {len(files_data)} files")
    return JSONResponse({"task_id": task_id, "message": f"Upload started for {len(files_data)} files"})

@app.get("/upload/status/{task_id}")
async def upload_status(task_id: str):
    """Get the status of an upload task with timeout detection"""
    if task_id not in UPLOAD_STATUS:
        raise HTTPException(status_code=404, detail="Upload task not found")
    
    status = UPLOAD_STATUS[task_id].copy()
    
    # Check for timeout (uploads taking longer than 10 minutes)
    if status["status"] == "processing" and "started_at" in status:
        elapsed = datetime.now() - status["started_at"]
        last_activity_elapsed = datetime.now() - status.get("last_activity", status["started_at"])
        
        # Total timeout: 10 minutes
        if elapsed.total_seconds() > 600:
            UPLOAD_STATUS[task_id]["status"] = "error"
            UPLOAD_STATUS[task_id]["errors"].append("Upload timeout: Process took longer than 10 minutes")
            UPLOAD_STATUS[task_id]["current_file"] = None
            print(f"[UPLOAD] Task {task_id} timed out after {elapsed.total_seconds():.1f} seconds")
            status = UPLOAD_STATUS[task_id].copy()
        # Activity timeout: no progress for 2 minutes
        elif last_activity_elapsed.total_seconds() > 120:
            UPLOAD_STATUS[task_id]["status"] = "error"
            UPLOAD_STATUS[task_id]["errors"].append("Upload stuck: No activity for more than 2 minutes")
            UPLOAD_STATUS[task_id]["current_file"] = None
            print(f"[UPLOAD] Task {task_id} stuck - no activity for {last_activity_elapsed.total_seconds():.1f} seconds")
            status = UPLOAD_STATUS[task_id].copy()
    
    # Clean up completed tasks older than 5 minutes
    if status["status"] in ["completed", "error"]:
        # You could add cleanup logic here if needed
        pass
    
    # Remove internal timestamps from response
    if "started_at" in status:
        del status["started_at"]
    if "last_activity" in status:
        del status["last_activity"]
    
    return JSONResponse(status)

# Add a simple test endpoint to see if we can receive any POST data
@app.post("/upload-test")
async def upload_test(request: Request):
    print("Upload test endpoint called")
    form = await request.form()
    print(f"Form data: {dict(form)}")
    return {"received": "ok"}

@app.post("/image/{id}/toggle")
def toggle_enable(id: int, db: Session = Depends(get_db)):
    img = db.get(Image, id)
    if not img: return JSONResponse({"error":"not found"}, status_code=404)
    img.enabled = not img.enabled
    db.commit()
    return {"enabled": img.enabled}

@app.post("/image/{id}/update")
def update_image(id: int,
                 title: str = Form(""),
                 description: str = Form(""),
                 sort_order: int = Form(None),
                 crop_x: float = Form(None),
                 crop_y: float = Form(None),
                 crop_width: float = Form(None),
                 crop_height: float = Form(None),
                 preserve_aspect_ratio: bool = Form(False),
                 db: Session = Depends(get_db)):
    img = db.get(Image, id)
    if not img: return JSONResponse({"error":"not found"}, status_code=404)
    img.title = title; img.description = description
    if sort_order is not None: img.sort_order = sort_order
    if crop_x is not None: img.crop_x = crop_x
    if crop_y is not None: img.crop_y = crop_y
    if crop_width is not None: img.crop_width = crop_width
    if crop_height is not None: img.crop_height = crop_height
    img.preserve_aspect_ratio = preserve_aspect_ratio
    db.commit(); return {"ok": True}

@app.post("/image/{id}/delete")
def delete_image(id: int, db: Session = Depends(get_db)):
    s = db.query(Settings).first()
    img = db.get(Image, id)
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

    # Try to detect Inky hardware info
    hardware = None
    try:
        from utils.eframe_inky import inky
        import sys
        if inky:
            color_map = {
                "red": "#e11d2a",
                "black": "#222",
                "white": "#fff",
                "yellow": "#ffe600",
                "green": "#0f0",
                "blue": "#00f"
            }
            # Supported colors
            supported_colours = getattr(inky, "supported_colours", [getattr(inky, "colour", "unknown")])
            # Model name
            model = getattr(inky, "__class__", type(inky)).__name__
            # Border color
            border = getattr(inky, "border", None)
            # EEPROM info
            eeprom = getattr(inky, "eeprom", None)
            # Library version
            try:
                import inky
                version = getattr(inky, "__version__", "unknown")
            except Exception:
                version = "unknown"
            # Detection type
            detect_type = "auto" if "auto" in str(type(inky)).lower() else "manual"
            hardware = {
                "colour": getattr(inky, "colour", "unknown"),
                "resolution": getattr(inky, "resolution", [800, 480]),
                "colors": [
                    {"name": c.title(), "css": color_map.get(c, "#888")} for c in supported_colours
                ],
                "supported_colours": supported_colours,
                "model": model,
                "border": border,
                "eeprom": eeprom,
                "version": version,
                "detect_type": detect_type
            }
    except Exception as e:
        hardware = None

    return templates.TemplateResponse("settings.html", {
        "request": request,
        "settings": s,
        "dev_mode": is_dev_mode(),
        "hardware": hardware
    })

# app.py – REPLACE the existing /settings handler with this:
@app.post("/settings", name="settings")
def update_settings(
    interval_ms: int = Form(...),
    order_mode: str = Form(...),
    slideshow_enabled: int = Form(...),
    image_root: str = Form(...),
    thumb_root: str = Form(...),
    resolution: str = Form(...),  # e.g. "800,480"
    border_color: str = Form(None),
    db: Session = Depends(get_db)
):
    s = db.query(Settings).first()
    s.interval_ms = interval_ms
    s.order_mode = order_mode
    s.slideshow_enabled = bool(slideshow_enabled)
    s.image_root = image_root.strip()
    s.thumb_root = thumb_root.strip()
    s.resolution = resolution.strip()

    # Set border color if hardware is detected and value provided
    if border_color:
        try:
            from utils.eframe_inky import inky
            if inky and hasattr(inky, "set_border"):
                inky.set_border(border_color)
        except Exception as e:
            print(f"[SETTINGS] Failed to set Inky border color: {e}")

    # Make sure folders exist after edits
    ensure_dirs(s.image_root, s.thumb_root, os.path.dirname("static/current.jpg"))

    db.commit()
    return RedirectResponse("/settings", status_code=303)

@app.post("/recalculate-crops")
def recalculate_crops(db: Session = Depends(get_db)):
    """
    Recalculate smart crop defaults for existing images that use full-frame crops.
    Useful for applying smart defaults to images uploaded before this feature.
    """
    s = db.query(Settings).first()
    if not s or not s.resolution:
        return JSONResponse({"error": "No display resolution configured"}, status_code=400)
    
    # Find images that are using default full-frame crop (likely uploaded before smart crops)
    images = db.query(Image).filter(
        Image.crop_x == 0,
        Image.crop_y == 0, 
        Image.crop_width == 100,
        Image.crop_height == 100
    ).all()
    
    updated_count = 0
    for img in images:
        if img.width and img.height:
            crop_x, crop_y, crop_width, crop_height = calculate_smart_crop(
                img.width, img.height, s.resolution
            )
            
            # Only update if the smart crop is different from current (not already perfect aspect ratio)
            if not (crop_x == 0 and crop_y == 0 and crop_width == 100 and crop_height == 100):
                img.crop_x = crop_x
                img.crop_y = crop_y
                img.crop_width = crop_width
                img.crop_height = crop_height
                updated_count += 1
    
    db.commit()
    return {"updated_count": updated_count, "total_checked": len(images)}

@app.post("/show-now/{id}")
def show_now(id: int, db: Session = Depends(get_db)):
    s = db.query(Settings).first()
    img = db.get(Image, id)
    if not img: return JSONResponse({"error":"not found"}, status_code=404)
    
    src = os.path.join(s.image_root, img.filename)
    render_to_output(src, "static/current.jpg", s.resolution, 
                    img.crop_x or 0, img.crop_y or 0, 
                    img.crop_width or 100, img.crop_height or 100,
                    img.preserve_aspect_ratio or False)
    
    # Queue the display update (non-blocking)
    queue_display("static/current.jpg", img.id)
    
    # Return immediately - display will happen in background
    return {"ok": True, "queued": True}

def pick_next(db: Session, s: Settings) -> Image | None:
    q = db.query(Image).filter(Image.enabled == True)

    if s.order_mode == "random":
        imgs = q.all()
        return random.choice(imgs) if imgs else None

    # Prefer images never shown, then least-recently shown.
    never_shown_first = case((Image.last_shown_at.is_(None), 0), else_=1)

    if s.order_mode == "custom":
        # honor custom sort first when tie-breaking
        return (
            q.order_by(
                never_shown_first.asc(),
                Image.last_shown_at.asc(),
                Image.sort_order.asc(),
                Image.created_at.asc(),
            )
            .first()
        )
    else:  # "added"
        # show by added time when tie-breaking
        return (
            q.order_by(
                never_shown_first.asc(),
                Image.last_shown_at.asc(),
                Image.created_at.asc(),
                Image.sort_order.asc(),
            )
            .first()
        )

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
                                         "static/current.jpg", s.resolution,
                                         img.crop_x or 0, img.crop_y or 0, 
                                         img.crop_width or 100, img.crop_height or 100,
                                         img.preserve_aspect_ratio or False)
                        
                        # Queue the display update (non-blocking)
                        queue_display("static/current.jpg", img.id)
                        
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

    print(f"\033[1;92mINFO:     Local machine IP address: \033[1mhttp://{local_ip}:8080\033[0m")

    # Use reload only in development mode
    use_reload = is_dev_mode()
    if use_reload:
        print("INFO:     Development mode - auto-reload enabled")
        # For reload to work, we need to pass the app as an import string
        uvicorn.run("app:app", host="0.0.0.0", port=8080, reload=True)
    else:
        print("INFO:     Production mode - auto-reload disabled")
        # In production, we can pass the app object directly
        uvicorn.run(app, host="0.0.0.0", port=8080, reload=False)

