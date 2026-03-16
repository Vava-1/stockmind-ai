import os
import logging
import re
import json
from datetime import datetime
from typing import List, Dict, Any

import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# --- NEW SDK IMPORTS ---
from google import genai
from groq import Groq

from core.database import get_db_connection, load_inventory_from_db
from core.config import settings
from services.scheduler import start_scheduler

# --- 1. Initialize Environment & Logging ---
load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('StockMind-Enterprise-Core')

# Enterprise White-Labeling (Defaults to GIVA TECH if not set in .env)
CLIENT_NAME = os.getenv("CLIENT_COMPANY_NAME", "GIVA TECH Ltd.")

# --- 2. THE DUAL-BRAIN ORCHESTRATOR ---
class DualBrainOrchestrator:
    """Enterprise-grade AI routing system with seamless Groq fallback."""
    def __init__(self):
        # Primary Engine: Google Gemini (New SDK)
        self.gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        # Fallback Engine: Groq (Llama 3)
        self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    def build_enterprise_context(self) -> str:
        """Universal Data Hook with Agentic Action capabilities."""
        inventory = load_inventory_from_db()
        total_items = len(inventory) if inventory else 0
        
        return (
            f"[SYSTEM PROTOCOL]\n"
            f"You are StockMind AI, the sovereign inventory intelligence agent for {CLIENT_NAME}.\n"
            f"LIVE DATA TELEMETRY: You currently monitor {total_items} distinct product lines in the master database.\n\n"
            f"=== NEW PRODUCT PROTOCOL ===\n"
            f"If the user asks to add a new product, you must collect these 6 fields: "
            f"1. product_id (Ask them, or offer to generate a random one like GT-PROD-XXXX) "
            f"2. product_name "
            f"3. product_category "
            f"4. current_stock (Must be a number) "
            f"5. unit_price (Must be a number) "
            f"6. supplier_name\n"
            f"Ask for these conversationally. DO NOT proceed until you have all 6.\n"
            f"Once you have all 6 confirmed by the user, you MUST append this exact JSON block at the very end of your response, enclosed in triple slashes:\n"
            f'/// {{"action": "ADD_PRODUCT", "id": "...", "name": "...", "category": "...", "stock": 0, "price": 0.0, "supplier": "..."}} ///\n'
            f"============================\n"
            f"DIRECTIVE: Be brilliant, highly analytical, and strictly professional. Format data cleanly.\n"
            f"[/SYSTEM PROTOCOL]\n\n"
        )

    def process_query(self, user_query: str, chat_history: List[Dict[str, Any]]) -> str:
        # 1. Compile stateless memory payload (Works for BOTH Gemini and Groq)
        system_prompt = self.build_enterprise_context()
        memory_string = "\n".join([f"{msg['role'].upper()}: {msg['content']}" for msg in chat_history[-5:]]) # Keep last 5 turns to save tokens
        
        full_payload = f"{system_prompt}PRIOR CHAT MEMORY:\n{memory_string}\n\nUSER: {user_query}\nAGENT:"

        # 2. Attempt Primary Engine (Gemini 2.5 Flash)
        try:
            logger.info("🧠 Routing to Primary Engine (Gemini 2.5 Flash)...")
            response = self.gemini_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=full_payload,
            )
            return response.text
            
        except Exception as gemini_err:
            logger.warning(f"⚠️ Primary Engine offline or rejected prompt: {gemini_err}. Executing instant failover to Groq...")
            
            # 3. Seamless Fallback Engine (Groq Llama-3)
            try:
                groq_response = self.groq_client.chat.completions.create(
                    messages=[{"role": "user", "content": full_payload}],
                    model="llama3-8b-8192", 
                    temperature=0.3 # Keep it highly logical
                )
                return groq_response.choices[0].message.content
                
            except Exception as groq_err:
                logger.error(f"🚨 CRITICAL CASCADE FAILURE: Both AI engines offline. Details: {groq_err}")
                raise HTTPException(status_code=503, detail="Enterprise AI network temporarily unreachable.")

# Instantiate the Sovereign Brain
ai_orchestrator = DualBrainOrchestrator()

# --- 3. FASTAPI SERVER SETUP ---
app = FastAPI(title=f'StockMind AI - {CLIENT_NAME}', version='3.0.0-Enterprise')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)

# --- 4. DATA STRUCTURES ---
class SaleRequest(BaseModel):
    product_id: str
    qty: int
    sale_price: float

class ChatRequest(BaseModel):
    query: str
    history: List[Dict[str, Any]] = []

# --- 5. API ENDPOINTS ---
@app.get('/health')
async def health_check():
    return {
        'status': 'online',
        'client_tenant': CLIENT_NAME,
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
                raise HTTPException(status_code=404, detail="Product not found in master ledger.")
                
            new_stock = result['current_stock']
            
            # Record Revenue
            cur.execute("""
                INSERT INTO sales_ledger (product_id, qty_sold, sale_price_usd)
                VALUES (%s, %s, %s)
            """, (req.product_id, req.qty, req.sale_price))
            conn.commit()

            # Autonomous Out-of-Stock Alerting
            if new_stock <= 0:
                logger.warning(f"🚨 ALERT: {req.product_id} depleted. Generating reorder sequence...")

        return {
            "status": "success", 
            "product_id": req.product_id,
            "remaining_stock": new_stock, 
            "revenue_added": req.qty * req.sale_price
        }
    except Exception as e:
        logger.error(f"Ledger processing failed: {e}")
        raise HTTPException(status_code=500, detail="Internal ledger error.")
    finally:
        conn.close()

@app.post('/chat')
async def stockmind_chat(req: ChatRequest):
    """The central communication hub. Intercepts AI commands and writes to the DB."""
    try:
        # 1. Get the raw text reply from the AI Brain
        ai_reply = ai_orchestrator.process_query(req.query, req.history)
        
        # 2. ACTION INTERCEPTOR: Look for the hidden /// JSON /// block
        match = re.search(r'///\s*(\{.*?\})\s*///', ai_reply, re.DOTALL)
        
        if match:
            try:
                # Parse the JSON the AI generated
                action_data = json.loads(match.group(1))
                
                if action_data.get("action") == "ADD_PRODUCT":
                    # Connect to the database and insert the new product
                    conn = get_db_connection()
                    with conn.cursor() as cur:
                        cur.execute("""
                            INSERT INTO inventory_master 
                            (product_id, product_name, product_category, current_stock, unit_price, supplier_name)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (
                            action_data["id"], action_data["name"], action_data["category"], 
                            int(action_data["stock"]), float(action_data["price"]), action_data["supplier"]
                        ))
                        conn.commit()
                    conn.close()
                    
                    # Remove the hidden JSON from the user's view and add a success badge
                    clean_reply = ai_reply.replace(match.group(0), "")
                    ai_reply = clean_reply + "\n\n✅ **SYSTEM ALERT:** Product successfully committed to the master database."
                    logger.info(f"Agent autonomously added product: {action_data['name']}")
                    
            except Exception as action_err:
                logger.error(f"AI generated invalid action data: {action_err}")
                clean_reply = ai_reply.replace(match.group(0), "")
                ai_reply = clean_reply + "\n\n⚠️ **SYSTEM ALERT:** Attempted to add product, but the data format was corrupted."

        return {"reply": ai_reply.strip()}
        
    except HTTPException as http_exc:
        # Pass through the 503 error if both brains fail
        raise http_exc
    except Exception as e:
        logger.error(f"Unexpected Chat API Error: {e}")
        return {"reply": "⚠️ System encountering unknown network anomalies."}

# --- 6. SERVER STARTUP ---
@app.on_event('startup')
async def startup():
    logger.info(f"Initializing StockMind AI Systems for {CLIENT_NAME}...")
    start_scheduler()

if __name__ == '__main__':
    uvicorn.run("main:app", host='0.0.0.0', port=settings.PORT, reload=True)