#!/usr/bin/env python3
"""
Development utility script to remove all image data and files.
This will delete all images from the database and file system.
USE WITH CAUTION - THIS CANNOT BE UNDONE!
"""

import os
import shutil
from database import SessionLocal
from models import Image, Settings

def count_files_in_directory(directory):
    """Count files in a directory"""
    if not os.path.exists(directory):
        return 0
    try:
        return len([f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))])
    except (OSError, PermissionError):
        return 0

def cleanup_images():
    """Remove all image data and files"""
    
    print("🗑️  Image Cleanup Utility")
    print("=" * 50)
    print("⚠️  WARNING: This will permanently delete ALL image data!")
    print("   - All database records will be removed")
    print("   - All uploaded image files will be deleted")
    print("   - All thumbnail files will be deleted")
    print("   - The current display image will be cleared")
    print()
    
    # Get database session
    db = SessionLocal()
    
    try:
        # Count images in database
        image_count = db.query(Image).count()
        print(f"📊 Database contains: {image_count} image records")
        
        # Get settings to find file directories
        settings = db.query(Settings).first()
        if not settings:
            print("❌ No settings found in database")
            return
        
        # Count files in directories
        uploads_count = count_files_in_directory(settings.image_root)
        thumbs_count = count_files_in_directory(settings.thumb_root)
        current_exists = os.path.exists("static/current.jpg")
        
        print(f"📁 Upload directory ({settings.image_root}): {uploads_count} files")
        print(f"🖼️  Thumbnail directory ({settings.thumb_root}): {thumbs_count} files")
        print(f"🎯 Current display image: {'exists' if current_exists else 'not found'}")
        
        print()
        print("📋 Summary:")
        print(f"   • {image_count} database records")
        print(f"   • {uploads_count} upload files")
        print(f"   • {thumbs_count} thumbnail files")
        print(f"   • Current display image: {'yes' if current_exists else 'no'}")
        
        if image_count == 0 and uploads_count == 0 and thumbs_count == 0 and not current_exists:
            print()
            print("✅ No images found to clean up!")
            return
        
        print()
        print("⚠️  THIS ACTION CANNOT BE UNDONE!")
        
        # Triple confirmation
        confirm1 = input("Type 'DELETE' to confirm you want to remove all images: ").strip()
        if confirm1 != 'DELETE':
            print("❌ Cleanup cancelled")
            return
        
        confirm2 = input("Are you absolutely sure? Type 'YES' to proceed: ").strip()
        if confirm2 != 'YES':
            print("❌ Cleanup cancelled")
            return
        
        print()
        print("🗑️  Starting cleanup...")
        
        # Remove database records
        if image_count > 0:
            deleted_count = db.query(Image).delete()
            db.commit()
            print(f"✅ Removed {deleted_count} database records")
        
        # Remove upload files
        if uploads_count > 0 and os.path.exists(settings.image_root):
            try:
                for filename in os.listdir(settings.image_root):
                    file_path = os.path.join(settings.image_root, filename)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                print(f"✅ Removed {uploads_count} upload files")
            except Exception as e:
                print(f"⚠️  Error removing upload files: {e}")
        
        # Remove thumbnail files
        if thumbs_count > 0 and os.path.exists(settings.thumb_root):
            try:
                for filename in os.listdir(settings.thumb_root):
                    file_path = os.path.join(settings.thumb_root, filename)
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                print(f"✅ Removed {thumbs_count} thumbnail files")
            except Exception as e:
                print(f"⚠️  Error removing thumbnail files: {e}")
        
        # Remove current display image
        if current_exists:
            try:
                os.remove("static/current.jpg")
                print("✅ Removed current display image")
            except Exception as e:
                print(f"⚠️  Error removing current display image: {e}")
        
        print()
        print("🎉 Cleanup completed successfully!")
        print("   Your image frame is now ready for fresh content.")
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")
        db.rollback()
    finally:
        db.close()

def show_status_only():
    """Show current status without cleanup"""
    print("📊 Image Status Report")
    print("=" * 30)
    
    db = SessionLocal()
    try:
        # Count images in database
        image_count = db.query(Image).count()
        print(f"Database records: {image_count}")
        
        # Get settings
        settings = db.query(Settings).first()
        if settings:
            uploads_count = count_files_in_directory(settings.image_root)
            thumbs_count = count_files_in_directory(settings.thumb_root)
            print(f"Upload files: {uploads_count}")
            print(f"Thumbnail files: {thumbs_count}")
        
        current_exists = os.path.exists("static/current.jpg")
        print(f"Current display: {'exists' if current_exists else 'none'}")
        
    except Exception as e:
        print(f"Error getting status: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg in ['--status', '-s']:
            show_status_only()
        elif arg in ['--help', '-h']:
            print("🗑️  Image Cleanup Utility")
            print("=" * 50)
            print("A development tool for cleaning up all image data and files.")
            print()
            print("Usage:")
            print("  python3 cleanup_images.py           # Interactive cleanup")
            print("  python3 cleanup_images.py --status  # Show status only")
            print("  python3 cleanup_images.py --help    # Show this help")
            print()
            print("Commands:")
            print("  (no args)     Interactive cleanup with confirmation")
            print("  -s, --status  Show current image count and file status")
            print("  -h, --help    Show this help message")
            print()
            print("⚠️  WARNING: The cleanup operation cannot be undone!")
            print("    Use --status first to see what will be removed.")
        else:
            print(f"Unknown option: {arg}")
            print("Use --help for usage information")
    else:
        cleanup_images()
