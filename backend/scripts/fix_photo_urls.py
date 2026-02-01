"""
Fix photo URLs in existing cases by replacing localhost with production URL.
Run this once after setting PUBLIC_BASE_URL on Render.
"""
import os
import sqlite3
import json
from pathlib import Path

# Get the new production URL from env or pass as argument
NEW_BASE_URL = os.getenv("PUBLIC_BASE_URL", "https://ecom-returns-copilot.onrender.com")
OLD_BASE_URL = "http://localhost:8000"

db_path = Path(__file__).parent.parent / "app" / "storage" / "cases.db"

def fix_photo_urls():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get all cases with photos
    cursor.execute("SELECT case_id, photo_urls_json FROM cases WHERE photo_urls_json IS NOT NULL AND photo_urls_json != '[]'")
    rows = cursor.fetchall()
    
    updated_count = 0
    for case_id, photo_urls_json in rows:
        photo_urls = json.loads(photo_urls_json)
        
        # Replace localhost with production URL
        new_urls = [url.replace(OLD_BASE_URL, NEW_BASE_URL) for url in photo_urls]
        
        if new_urls != photo_urls:
            cursor.execute(
                "UPDATE cases SET photo_urls_json = ? WHERE case_id = ?",
                (json.dumps(new_urls), case_id)
            )
            updated_count += 1
            print(f"✓ Updated {case_id}: {photo_urls[0]} → {new_urls[0]}")
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ Updated {updated_count} case(s)")

if __name__ == "__main__":
    print(f"Replacing {OLD_BASE_URL} with {NEW_BASE_URL}\n")
    fix_photo_urls()
