import functools
import traceback
import logging
from core.database import get_db_connection
from core.config import settings
from services.email_service import send_email

logger = logging.getLogger('StockMind-SelfHealing')

def diagnose_with_llm(error_trace: str) -> str:
    """Uses the LLM to analyze the Python traceback and suggest a fix."""
    prompt = f"You are the StockMind AI debugging agent. Analyze this Python error, explain what broke in 1-2 sentences, and suggest a fallback action:\n\n{error_trace}"
    
    # Try Groq first for fast diagnosis
    if settings.GROQ_API_KEY:
        try:
            from groq import Groq
            client = Groq(api_key=settings.GROQ_API_KEY)
            res = client.chat.completions.create(
                model='llama-3.3-70b-versatile',
                messages=[{'role': 'user', 'content': prompt}],
                max_tokens=200,
                temperature=0.2
            )
            return res.choices[0].message.content
        except Exception as e:
            logger.warning(f"Groq diagnosis failed: {e}")
            
    # Fallback to Gemini
    if settings.GEMINI_API_KEY:
        try:
            import google.generativeai as genai
            genai.configure(api_key=settings.GEMINI_API_KEY)
            model = genai.GenerativeModel('gemini-1.5-flash')
            return model.generate_content(prompt).text
        except Exception as e:
            logger.error(f"Gemini diagnosis failed: {e}")
            
    return "LLM Diagnosis unavailable. Manual debugging required."

def with_self_healing(fallback_return=None):
    """
    A decorator that wraps critical functions. If they crash, it catches the error,
    diagnoses it with AI, logs it to PostgreSQL, emails the engineering team, 
    and returns a safe fallback value to keep the system running.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                func_name = func.__name__
                error_trace = traceback.format_exc()
                logger.error(f"⚠️ Critical failure in '{func_name}'. Initiating self-healing...")
                
                # 1. AI Diagnosis
                diagnosis = diagnose_with_llm(error_trace)
                logger.info(f"Diagnosis complete for '{func_name}'.")
                
                # 2. Log to Database
                conn = get_db_connection()
                if conn:
                    try:
                        with conn.cursor() as cur:
                            cur.execute(
                                "INSERT INTO system_anomalies (error_traceback, agent_diagnosis) VALUES (%s, %s)",
                                (error_trace, diagnosis)
                            )
                        conn.commit()
                    except Exception as db_err:
                        logger.error(f"Failed to log anomaly to DB: {db_err}")
                    finally:
                        conn.close()
                        
                # 3. Email Alert to Engineering
                subject = f"⚠️ SYSTEM ANOMALY: '{func_name}' Failed"
                text_body = f"Function: {func_name}\nError:\n{error_trace}\n\nAgent Diagnosis:\n{diagnosis}"
                html_body = f"""
                <html><body style="font-family: monospace; background: #111827; color: #f87171; padding: 20px;">
                    <h2 style="color: #ef4444;">⚠️ SELF-HEALING LOG: {func_name}</h2>
                    <pre style="background: #000; padding: 15px; color: #fca5a5; overflow-x: auto; border-radius: 5px;">{error_trace}</pre>
                    <h3 style="color: #60a5fa;">AI Diagnosis:</h3>
                    <p style="color: #e2e8f0; font-size: 14px; line-height: 1.5;">{diagnosis}</p>
                    <p style="color: #9ca3af; font-size: 12px; margin-top: 20px;">System automatically returned fallback value to prevent crash.</p>
                </body></html>
                """
                # We send this to the main alert email (you can change this to engineering@givatech.com later)
                send_email(subject, text_body, html_body, settings.ALERT_EMAIL)
                
                return fallback_return
        return wrapper
    return decorator
