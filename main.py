import os
import logging
from datetime import datetime
from typing import List, Dict, Any

import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import google.generativeai as genai

from core.database import get_db_connection, load_inventory_from_db
from core.config import settings
from services.scheduler import start_scheduler

# --- 1. Initialize Environment & AI Brain ---
# This unlocks your .env file so the script can find your passwords and keys
load_dotenv()
# This plugs the key directly into the Google Gemini engine
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# --- 2. Setup Server Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('StockMind-API')

app = FastAPI(title='StockMind AI - Sovereign Enterprise Agent', version='2.0.0')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)

# --- 3. Pydantic Models (Data Structures) ---
class SaleRequest(BaseModel):
    product_id: str
    qty: int
    sale_price: float

class ChatRequest(BaseModel):
    query: str
    history: List[Dict[str, Any]] = []

# --- 4. API Endpoints ---

@app.get('/health')
async def health_check():
    return {
        'status': 'online',
        'database': 'connected' if get_db_connection() else 'disconnected',
        'timestamp': datetime.now().isoformat()
    }

@app.get('/inventory')
async def get_inventory():
    data = load_inventory_from_db()
    return {
        'total_products': len(data) if data else 0,
        'items': data
    }

@app.post('/sell')
async def record_sale(req: SaleRequest, background_tasks: BackgroundTasks):
    """Real-Time Ledger: Deducts stock and adds revenue the second a sale happens."""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=500, detail="Database connection error")
    
    try:
        from psycopg2.extras import RealDictCursor
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Update Stock Levels
            cur.execute("""
                UPDATE inventory_master 
                SET current_stock = current_stock - %s 
                WHERE product_id = %s RETURNING current_stock, product_category, supplier_name
            """, (req.qty, req.product_id))
            
            result = cur.fetchone()
            if not result:
                raise HTTPException(status_code=404, detail="Product not found")
                
            new_stock = result['current_stock']
            
            # Record Revenue in Ledger
            cur.execute("""
                INSERT INTO sales_ledger (product_id, qty_sold, sale_price_usd)
                VALUES (%s, %s, %s)
            """, (req.product_id, req.qty, req.sale_price))
            
            conn.commit()

            # Autonomous Out-of-Stock Trigger
            if new_stock <= 0:
                logger.warning(f"🚨 PRODUCT {req.product_id} OUT OF STOCK! Triggering alert...")

        return {
            "status": "success", 
            "product_id": req.product_id,
            "remaining_stock": new_stock, 
            "revenue_added_usd": req.qty * req.sale_price
        }
    except Exception as e:
        logger.error(f"Sale processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.post('/chat')
async def stockmind_chat(req: ChatRequest):
    """The AI Brain: Handles chat messages and remembers history."""
    try:
        # Load basic DB stats to give the AI context
        inventory = load_inventory_from_db()
        total_items = len(inventory) if inventory else 0
        
        # 1. Translate Streamlit history into Gemini's memory format
        gemini_history = []
        for msg in req.history:
            role = "model" if msg["role"] == "assistant" else "user"
            gemini_history.append({"role": role, "parts": [msg["content"]]})

        # 2. Setup the AI model
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # 3. Start a chat session with the formatted history
        chat = model.start_chat(history=gemini_history)
        
        # 4. Inject system instructions invisibly behind the user's prompt
        system_context = (
            f"[SYSTEM INSTRUCTION: You are StockMind AI, the official inventory management agent for GIVA TECH. "
            f"You currently have {total_items} items recorded in the PostgreSQL database. "
            f"Be professional, brilliant, and concise. Format your answers nicely.]\n\n"
        )
        final_prompt = system_context + req.query

        # 5. Send message and return the reply
        response = chat.send_message(final_prompt)
        return {"reply": response.text}
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return {"reply": f"⚠️ Connection error: {str(e)}. Make sure your GEMINI_API_KEY is correct in the .env file!"}

# --- 5. Server Startup ---
@app.on_event('startup')
async def startup():
    start_scheduler()

if __name__ == '__main__':
    logger.info(f"Starting StockMind AI on port {settings.PORT}...")
    uvicorn.run("main:app", host='0.0.0.0', port=settings.PORT, reload=True)