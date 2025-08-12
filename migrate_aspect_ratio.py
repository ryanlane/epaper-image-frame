#!/usr/bin/env python3
"""
Migration script to add preserve_aspect_ratio field to existing images table
"""

import sqlite3
import os

def migrate_aspect_ratio():
    db_path = "photo_frame.db"
    
    if not os.path.exists(db_path):
        print("Database file not found. No migration needed.")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if the column already exists
        cursor.execute("PRAGMA table_info(images)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'preserve_aspect_ratio' in columns:
            print("preserve_aspect_ratio column already exists. No migration needed.")
            return
        
        # Add the new column
        cursor.execute("""
            ALTER TABLE images 
            ADD COLUMN preserve_aspect_ratio BOOLEAN DEFAULT FALSE
        """)
        
        conn.commit()
        print("Successfully added preserve_aspect_ratio column to images table")
        print("All existing images default to crop-to-fill behavior (preserve_aspect_ratio = FALSE)")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_aspect_ratio()
