import logging
import os
from dotenv import load_dotenv
from database import get_connection

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate():
    conn = get_connection()
    if not conn:
        logger.error("Could not connect to database for migration.")
        return
    
    try:
        cursor = conn.cursor()
        
        # Check if column exists
        cursor.execute("""
            SELECT 1 FROM information_schema.columns 
            WHERE table_name='detection_counts' AND column_name='bicycle_count';
        """)
        exists = cursor.fetchone()
        
        if exists:
            logger.info("Dropping 'bicycle_count' column from 'detection_counts' table...")
            cursor.execute("ALTER TABLE detection_counts DROP COLUMN bicycle_count;")
            conn.commit()
            logger.info("Column 'bicycle_count' dropped successfully.")
        else:
            logger.info("Column 'bicycle_count' does not exist. Skipping.")
            
        cursor.close()
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
