import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from core.config import settings

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('StockMindDB')

def get_db_connection():
    """Establishes a connection to the PostgreSQL database."""
    try:
        conn = psycopg2.connect(
            dbname=settings.DB_NAME,
            user=settings.DB_USER,
            password=settings.DB_PASS,
            host=settings.DB_HOST,
            port=settings.DB_PORT
        )
        return conn
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return None

def load_inventory_from_db():
    """Fetches all products from the inventory_master table."""
    conn = get_db_connection()
    if not conn:
        logger.warning("Returning empty inventory due to database connection failure.")
        return []
    
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM inventory_master ORDER BY product_id ASC;")
            data = cur.fetchall()
            logger.info(f"Loaded {len(data)} products from database.")
            return data
    except Exception as e:
        logger.error(f"Failed to fetch inventory: {e}")
        return []
    finally:
        conn.close()

def execute_query(query, params=None, fetch=False):
    """Helper function to safely execute generic SQL queries."""
    conn = get_db_connection()
    if not conn: return None

    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            if fetch:
                return cur.fetchall()
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        return None
    finally:
        conn.close()
