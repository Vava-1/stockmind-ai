import schedule
import time
import threading
import logging
from datetime import datetime
from core.database import get_db_connection
from core.config import settings
from services.email_service import send_email

logger = logging.getLogger('StockMind-Scheduler')

def send_end_of_day_financials():
    """Calculates total daily revenue and sends the HTML report."""
    logger.info("Running End of Day Financial Rollup...")
    conn = get_db_connection()
    if not conn:
        logger.error("DB connection failed during financial rollup.")
        return

    try:
        from psycopg2.extras import RealDictCursor
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Aggregate today's sales directly from the SQL database
            cur.execute("""
                SELECT 
                    product_id, 
                    SUM(qty_sold) as total_qty, 
                    AVG(sale_price_usd) as avg_sale_price,
                    SUM(total_revenue_usd) as product_revenue
                FROM sales_ledger
                WHERE DATE(transaction_time) = CURRENT_DATE
                GROUP BY product_id
                ORDER BY product_revenue DESC
            """)
            daily_sales = cur.fetchall()
            
            total_daily_revenue = sum(item['product_revenue'] for item in daily_sales) if daily_sales else 0

        # Format the Financial Report Subject
        subject = f"💰 Daily Financial Rollup - {datetime.now().strftime('%b %d, %Y')}"
        
        # Plain Text Fallback
        text_body = f"STOCKMIND AI: END OF DAY REVENUE REPORT\n"
        text_body += f"Total Revenue Today: ${total_daily_revenue:,.2f}\n"
        text_body += "=" * 50 + "\n\n"
        
        # Professional HTML Table
        html_body = f"""
        <html>
        <body style="font-family: monospace; background-color: #0a0f1e; color: #e2e8f0; padding: 24px;">
            <div style="max-width: 600px; margin: auto; background-color: #111827; padding: 20px; border-radius: 8px; border-top: 4px solid #10b981;">
                <h2 style="color: #10b981; letter-spacing: 2px;">DAILY FINANCIAL ROLLUP</h2>
                <h3 style="color: #ffffff; font-size: 24px;">Total Revenue: ${total_daily_revenue:,.2f}</h3>
                <hr style="border-color: #374151; margin: 20px 0;">
                <table style="width: 100%; text-align: left; border-collapse: collapse;">
                    <tr style="color: #9ca3af; border-bottom: 1px solid #374151;">
                        <th style="padding: 8px 0;">Product ID</th>
                        <th>Qty Sold</th>
                        <th>Avg Price</th>
                        <th style="text-align: right;">Revenue</th>
                    </tr>
        """
        
        for sale in daily_sales:
            text_body += f"[{sale['product_id']}] - Qty: {sale['total_qty']} | Avg Price: ${sale['avg_sale_price']:.2f} | Revenue: ${sale['product_revenue']:,.2f}\n"
            html_body += f"""
                    <tr style="border-bottom: 1px solid #1f2937;">
                        <td style="padding: 8px 0;">{sale['product_id']}</td>
                        <td>{sale['total_qty']}</td>
                        <td>${sale['avg_sale_price']:.2f}</td>
                        <td style="text-align: right; color: #10b981;">${sale['product_revenue']:,.2f}</td>
                    </tr>
            """
            
        html_body += """
                </table>
                <p style="font-size: 11px; color: #4b5563; margin-top: 20px;">
                    Generated autonomously by StockMind AI at 23:59 System Time.
                </p>
            </div>
        </body>
        </html>
        """

        # Send to the finance team (using ALERT_EMAIL from .env for now)
        send_email(subject, text_body, html_body, settings.ALERT_EMAIL) 
        logger.info("End of day financial report sent successfully.")
        
    except Exception as e:
        logger.error(f"Failed to run financial rollup: {e}")
    finally:
        conn.close()

def start_scheduler():
    """Initializes the background daemon thread."""
    logger.info("Initializing background scheduler. End-of-day set for 23:59.")
    
    # Schedule the daily financial report
    schedule.every().day.at("23:59").do(send_end_of_day_financials)
    
    # You can easily add more scheduled tasks here, like:
    # schedule.every(4).hours.do(scout_new_products)

    def run_loop():
        while True:
            schedule.run_pending()
            time.sleep(60) # Check every minute

    # Run in a background thread so it doesn't block FastAPI
    t = threading.Thread(target=run_loop, daemon=True)
    t.start()
