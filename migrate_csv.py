import os
import csv
import psycopg2
from dotenv import load_dotenv

# --- 1. Load the Live Database Connection ---
load_dotenv()
DB_URL = os.getenv("DATABASE_URL") 
CSV_FILE_PATH = "giva_tech_inventory_master.csv" 

def migrate_data():
    if not DB_URL:
        print("🚨 CRITICAL: DATABASE_URL is missing from your .env file!")
        return

    if not os.path.exists(CSV_FILE_PATH):
        print(f"🚨 ERROR: Could not find '{CSV_FILE_PATH}' on your laptop.")
        return

    print("🔌 Establishing secure connection to Railway Cloud Database...")
    conn = None
    cursor = None
    
    try:
        conn = psycopg2.connect(DB_URL)
        cursor = conn.cursor()

        print("🛡️ Verifying master database schema...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventory_master (
                product_id VARCHAR(50) PRIMARY KEY,
                product_name VARCHAR(255),
                product_category VARCHAR(100),
                current_stock INT DEFAULT 0,
                unit_price NUMERIC(10, 2),
                supplier_name VARCHAR(255),
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE TABLE IF NOT EXISTS sales_ledger (
                sale_id SERIAL PRIMARY KEY,
                product_id VARCHAR(50) REFERENCES inventory_master(product_id),
                qty_sold INT NOT NULL,
                sale_price_usd NUMERIC(10, 2) NOT NULL,
                sale_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()

        print(f"📂 Reading 5,000+ item telemetry from {CSV_FILE_PATH}...")
        
        with open(CSV_FILE_PATH, mode='r', encoding='utf-8-sig') as file:
            csv_reader = csv.DictReader(file)
            
            success_count = 0
            for row in csv_reader:
                # --- ENTERPRISE MAPPING ENGINE ---
                # Matches the exact capital letters from your dataset
                product_id = row.get('Product_ID')
                if not product_id or str(product_id).strip() == "":
                    continue
                
                # Auto-generate a cool product name since your CSV doesn't have one
                category = row.get('Product_Category', 'Tech Hardware').strip()
                item_number = product_id.split('-')[-1] if '-' in product_id else "000"
                generated_name = f"GIVA {category} Series-{item_number}"
                
                # Safely pull the exact columns from your data
                raw_stock = row.get('Current_Stock', 0)
                safe_stock = int(raw_stock) if raw_stock and str(raw_stock).strip() else 0
                
                raw_price = row.get('Retail_Price_USD', 0.0)
                safe_price = float(raw_price) if raw_price and str(raw_price).strip() else 0.0
                
                supplier = row.get('Supplier_Name', 'Unknown').strip()

                # Upsert into Database
                cursor.execute("""
                    INSERT INTO inventory_master 
                        (product_id, product_name, product_category, current_stock, unit_price, supplier_name)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (product_id) 
                    DO UPDATE SET 
                        product_name = EXCLUDED.product_name,
                        current_stock = EXCLUDED.current_stock,
                        unit_price = EXCLUDED.unit_price,
                        supplier_name = EXCLUDED.supplier_name,
                        last_updated = CURRENT_TIMESTAMP;
                """, (product_id, generated_name, category, safe_stock, safe_price, supplier))
                
                success_count += 1
                # Print a progress update every 1000 items so you know it's working
                if success_count % 1000 == 0:
                    print(f"⏳ Processed {success_count} items...")

        conn.commit()
        print(f"✅ BINGO! Successfully teleported {success_count} products into the Railway Cloud!")

    except Exception as e:
        print(f"❌ Migration sequence failed: {e}")
        if conn:
            conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    print("🚀 Initiating Massive Enterprise Data Migration...")
    migrate_data()