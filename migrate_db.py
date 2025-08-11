#!/usr/bin/env python3
"""
Migration script to add crop columns to existing database
"""

import sqlite3
import os

def migrate_database():
    db_path = "photo_frame.db"
    
    if not os.path.exists(db_path):
        print("Database does not exist, no migration needed")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if crop_x column already exists
        cursor.execute("PRAGMA table_info(images)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'crop_x' in columns:
            print("Crop columns already exist, no migration needed")
            return
        
        print("Adding crop columns to images table...")
        
        # Add the crop columns
        cursor.execute("ALTER TABLE images ADD COLUMN crop_x INTEGER DEFAULT 0")
        cursor.execute("ALTER TABLE images ADD COLUMN crop_y INTEGER DEFAULT 0") 
        cursor.execute("ALTER TABLE images ADD COLUMN crop_width INTEGER DEFAULT 100")
        cursor.execute("ALTER TABLE images ADD COLUMN crop_height INTEGER DEFAULT 100")
        
        conn.commit()
        print("Migration completed successfully!")
        
    except Exception as e:
        print(f"Migration error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_database()
