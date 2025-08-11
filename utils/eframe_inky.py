from PIL import Image
import os
from dotenv import load_dotenv
from inky.auto import auto

load_dotenv()
use_fake = os.getenv("ENVIRONMENT") == "development"
if not use_fake:
    inky = auto(ask_user=True, verbose=True)

def get_inky_resolution():
    return [800,480] if use_fake else [inky.resolution[0], inky.resolution[1]]

def show_on_inky(imagepath, saturation=0.5):
    if use_fake:
        print(f"[DEV] Would display: {imagepath}")
        return
    img = Image.open(imagepath)
    inky.set_image(img, saturation=saturation)
    inky.show()
