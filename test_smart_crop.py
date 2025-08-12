#!/usr/bin/env python3
"""
Test script to demonstrate smart crop calculations
"""

def calculate_smart_crop(image_width, image_height, display_resolution):
    """
    Calculate smart default crop that centers the image if it needs cropping.
    Returns (crop_x, crop_y, crop_width, crop_height) as percentages.
    """
    if not display_resolution or ',' not in display_resolution:
        return 0, 0, 100, 100
    
    try:
        display_width, display_height = map(int, display_resolution.split(','))
        display_aspect = display_width / display_height
        image_aspect = image_width / image_height
        
        if abs(display_aspect - image_aspect) < 0.01:
            return 0, 0, 100, 100
        
        if image_aspect > display_aspect:
            # Image is wider - crop horizontally, center left-right
            crop_height = 100
            crop_width = (display_aspect / image_aspect) * 100
            crop_x = (100 - crop_width) / 2
            crop_y = 0
        else:
            # Image is taller - crop vertically, center top-bottom  
            crop_width = 100
            crop_height = (image_aspect / display_aspect) * 100
            crop_x = 0
            crop_y = (100 - crop_height) / 2
        
        return round(crop_x, 2), round(crop_y, 2), round(crop_width, 2), round(crop_height, 2)
        
    except (ValueError, ZeroDivisionError):
        return 0, 0, 100, 100

# Test cases
print("Smart Crop Calculator Demo")
print("=" * 40)

display_res = "800,480"  # Typical e-ink display resolution (landscape)
print(f"Display Resolution: {display_res} (aspect ratio: {800/480:.2f})")
print()

test_cases = [
    ("Portrait Photo", 3000, 4000),      # Tall image
    ("Landscape Photo", 4000, 3000),     # Wide image  
    ("Square Photo", 2000, 2000),        # Square image
    ("Ultra Wide", 6000, 2000),          # Very wide
    ("Ultra Tall", 2000, 6000),          # Very tall
    ("Perfect Match", 1600, 960),        # Already correct aspect ratio
]

for name, width, height in test_cases:
    crop_x, crop_y, crop_width, crop_height = calculate_smart_crop(width, height, display_res)
    aspect_ratio = width / height
    
    print(f"{name}: {width}x{height} (aspect: {aspect_ratio:.2f})")
    print(f"  Smart Crop: x={crop_x}%, y={crop_y}%, w={crop_width}%, h={crop_height}%")
    
    if crop_x == 0 and crop_y == 0 and crop_width == 100 and crop_height == 100:
        print("  → No cropping needed (perfect aspect ratio)")
    elif crop_x > 0:
        print(f"  → Crop {crop_width}% width, centered horizontally")
    elif crop_y > 0:
        print(f"  → Crop {crop_height}% height, centered vertically")
    print()
