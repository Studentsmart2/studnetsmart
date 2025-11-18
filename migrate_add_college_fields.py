"""
Database Migration: Add college_type and college_state fields to User table

This script adds two new columns to the User table:
- college_type: VARCHAR(50) - Type of college (BTech, Medical, Associate)
- college_state: VARCHAR(100) - State where the college is located

Run this script once to update the database schema.
"""

import sqlite3
import os

# Get the database path
# Try multiple possible locations
DB_PATH = os.path.join(os.path.dirname(__file__), 'edutrade.db')
if not os.path.exists(DB_PATH):
    DB_PATH = os.path.join(os.path.dirname(__file__), 'instance', 'database.db')

def migrate():
    """Add college_type and college_state columns to User table"""

    print(f"Connecting to database: {DB_PATH}")

    if not os.path.exists(DB_PATH):
        print(f"ERROR: Database file not found at {DB_PATH}")
        print("Please ensure the application has been run at least once to create the database.")
        return False

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Check if columns already exist
        cursor.execute("PRAGMA table_info(user)")
        columns = [column[1] for column in cursor.fetchall()]

        changes_made = False

        # Add college_type column if it doesn't exist
        if 'college_type' not in columns:
            print("Adding college_type column...")
            cursor.execute("""
                ALTER TABLE user
                ADD COLUMN college_type VARCHAR(50)
            """)
            changes_made = True
            print("✓ college_type column added successfully")
        else:
            print("✓ college_type column already exists")

        # Add college_state column if it doesn't exist
        if 'college_state' not in columns:
            print("Adding college_state column...")
            cursor.execute("""
                ALTER TABLE user
                ADD COLUMN college_state VARCHAR(100)
            """)
            changes_made = True
            print("✓ college_state column added successfully")
        else:
            print("✓ college_state column already exists")

        # Commit changes
        if changes_made:
            conn.commit()
            print("\n✓ Migration completed successfully!")
        else:
            print("\n✓ No migration needed - columns already exist")

        # Verify the changes
        cursor.execute("PRAGMA table_info(user)")
        columns = cursor.fetchall()
        print("\nUser table schema:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")

        conn.close()
        return True

    except sqlite3.Error as e:
        print(f"ERROR: Database error occurred: {e}")
        return False
    except Exception as e:
        print(f"ERROR: Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("Database Migration: Add College Fields")
    print("=" * 60)
    print()

    success = migrate()

    print()
    print("=" * 60)
    if success:
        print("Migration Status: SUCCESS")
    else:
        print("Migration Status: FAILED")
    print("=" * 60)
