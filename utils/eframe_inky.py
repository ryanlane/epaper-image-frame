from PIL import Image
import os
from dotenv import load_dotenv

load_dotenv()

def is_dev_mode():
    """Check if application is running in development mode based on environment variable"""
    env = os.getenv('ENVIRONMENT', '').lower()
    return env in ('development', 'dev')

use_fake = is_dev_mode()

inky = None
if not use_fake:
    try:
        from inky.auto import auto
        inky = auto(ask_user=True, verbose=True)
    except ImportError:
        print("Warning: inky package not installed, running in fake mode")
        use_fake = True

def get_inky_resolution():
    if use_fake or inky is None:
        return [800, 480]
    return [inky.resolution[0], inky.resolution[1]]

def show_on_inky(imagepath, saturation=0.5):
    if use_fake or inky is None:
        print(f"[DEV] Would display: {imagepath}")
        return
    img = Image.open(imagepath)
    inky.set_image(img, saturation=saturation)
    inky.show()
