import os
import logging
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger('StockMind-Enterprise-Core')

def get_db_connection():
    """Establishes a secure connection to the Railway Enterprise Database."""
    db_url = os.getenv("DATABASE_URL")
    
    if not db_url:
        logger.error("🚨 CRITICAL: DATABASE_URL environment variable is missing!")
        return None
        
    try:
        conn = psycopg2.connect(db_url)
        return conn
    except Exception as e:
        logger.error(f"🚨 Database connection failed: {e}")
        return None

def load_inventory_from_db():
    """Pulls the live 5,000+ item telemetry into the AI brain."""
    conn = get_db_connection()
    if not conn:
        logger.warning("Returning empty inventory due to database connection failure.")
        return []
        
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # We fetch the exact columns you mapped in your migration script
            cur.execute("""
                SELECT product_id, product_name, product_category, 
                       current_stock, unit_price, supplier_name 
                FROM inventory_master
                ORDER BY product_name ASC;
            """)
            return cur.fetchall()
    except Exception as e:
        logger.error(f"Failed to load inventory: {e}")
        return []
    finally:
        if conn:
            conn.close()