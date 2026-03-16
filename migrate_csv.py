import csv
import os
import psycopg2
from dotenv import load_dotenv

# Load your secure .env variables
load_dotenv()

def migrate_data():
    print("Starting data migration...")
    
    # 1. Connect to PostgreSQL
    try:
        conn = psycopg2.connect(
            dbname="stockmind_db",               
            user=os.getenv("DB_USER", "postgres"),
            password="VavusDei2004",  # <--- Make sure your actual password is here!
            host=os.getenv("DB_HOST", "localhost"),
            port=os.getenv("DB_PORT", "5432")
        )
        cur = conn.cursor()
        print("Connected to PostgreSQL successfully.")
    except Exception as e:
        print(f"Database connection failed: {e}")
        return

    # CREATE THE TABLE IF IT DOES NOT EXIST
    print("Ensuring database table exists...")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS inventory_master (
            product_id VARCHAR(50) PRIMARY KEY,
            product_category VARCHAR(100),
            current_stock INTEGER,
            supplier_cost_usd DECIMAL(10, 2),
            lead_time_days INTEGER,
            daily_sales_velocity DECIMAL(10, 2),
            supplier_name VARCHAR(100),
            market_trend_score INTEGER,
            retail_price_usd DECIMAL(10, 2)
        );
    """)
    
    # CREATE THE SALES LEDGER TABLE FOR THE AI
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sales_ledger (
            transaction_id SERIAL PRIMARY KEY,
            product_id VARCHAR(50),
            qty_sold INTEGER,
            sale_price_usd DECIMAL(10, 2),
            total_revenue_usd DECIMAL(10, 2) GENERATED ALWAYS AS (qty_sold * sale_price_usd) STORED,
            transaction_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()

    # 2. Read the CSV file
    csv_file_path = "giva_tech_inventory_master.csv" 
    
    if not os.path.exists(csv_file_path):
        print(f"Error: Could not find '{csv_file_path}'. Make sure it is in the same folder as this script.")
        return

    success_count = 0
    error_count = 0

    print("Reading CSV and injecting into the database...")
    
    with open(csv_file_path, mode='r', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file)
        
        for raw_row in reader:
            # BULLETPROOF TRICK: Make all column names lowercase and strip hidden spaces
            row = {str(k).strip().lower(): v for k, v in raw_row.items()}
            
            try:
                # 3. Insert each row into the database
                cur.execute("""
                    INSERT INTO inventory_master (
                        product_id, product_category, current_stock, 
                        supplier_cost_usd, lead_time_days, daily_sales_velocity, 
                        supplier_name, market_trend_score, retail_price_usd
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (product_id) DO NOTHING;
                """, (
                    row['product_id'], 
                    row['product_category'], 
                    int(float(row['current_stock'])), 
                    float(row['supplier_cost_usd']), 
                    int(float(row['lead_time_days'])), 
                    float(row['daily_sales_velocity']), 
                    row['supplier_name'], 
                    int(float(row['market_trend_score'])), 
                    float(row['retail_price_usd'])
                ))
                success_count += 1
            except Exception as e:
                print(f"Error inserting {row.get('product_id', 'Unknown')}: {e}")
                error_count += 1
                conn.rollback() # Reset transaction state if one row fails
            else:
                conn.commit()

    print(f"\n✅ Migration complete! Successfully inserted {success_count} products.")
    if error_count > 0:
        print(f"⚠️ Failed to insert {error_count} products.")

    cur.close()
    conn.close()

if __name__ == "__main__":
    migrate_data()