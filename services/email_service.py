import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import logging
from core.config import settings

# Setup logging
logger = logging.getLogger('StockMind-Email')

def send_email(subject: str, text_content: str, html_content: str, to_email: str):
    """Core function to send an email via SMTP."""
    if not settings.SMTP_EMAIL or not settings.SMTP_PASSWORD:
        logger.warning("SMTP credentials not configured in .env! Skipping email send.")
        return False
        
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = settings.SMTP_EMAIL
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Attach both plain text and HTML versions
        msg.attach(MIMEText(text_content, 'plain'))
        msg.attach(MIMEText(html_content, 'html'))
        
        # Connect to Gmail SMTP Server (adjust if using Outlook/SendGrid)
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(settings.SMTP_EMAIL, settings.SMTP_PASSWORD)
            server.send_message(msg)
            
        logger.info(f"Email successfully sent to {to_email} | Subject: {subject}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False

def trigger_out_of_stock_alert(product_id: str, category: str, supplier: str):
    """Drafts and sends the emergency out-of-stock alert."""
    subject = f"🚨 URGENT: {product_id} is OUT OF STOCK"
    
    text_body = (
        f"STOCKMIND AI ALERT\n"
        f"==================\n"
        f"Product: {product_id}\nCategory: {category}\nSupplier: {supplier}\n\n"
        f"This product has hit 0 stock during live trading. Immediate reorder required."
    )
    
    html_body = f"""
    <html>
    <body style="font-family: monospace; background-color: #0a0f1e; color: #e2e8f0; padding: 24px;">
        <div style="max-width: 600px; margin: auto; background-color: #111827; padding: 20px; border-radius: 8px; border-left: 4px solid #ef4444;">
            <h2 style="color: #ef4444; letter-spacing: 2px;">STOCKMIND AI ALERT</h2>
            <p><strong>Product ID:</strong> {product_id}</p>
            <p><strong>Category:</strong> {category}</p>
            <p><strong>Supplier:</strong> {supplier}</p>
            <p style="color: #9ca3af; margin-top: 15px;">
                This product has hit 0 stock during live trading. Immediate reorder required to prevent revenue loss.
            </p>
            <hr style="border-color: #374151; margin-top: 20px;">
            <p style="font-size: 11px; color: #4b5563;">
                Generated autonomously by StockMind AI at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </p>
        </div>
    </body>
    </html>
    """
    
    # Send to the alert email configured in .env (e.g., General Manager)
    return send_email(subject, text_body, html_body, settings.ALERT_EMAIL)
