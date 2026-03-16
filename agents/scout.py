import os
from google.colab import files

# Ensure the 'agents' directory exists
os.makedirs("agents", exist_ok=True)

# ==========================================
# FILE 10: agents/scout.py (UPGRADED)
# ==========================================
scout_content = """import logging
from datetime import datetime
from core.config import settings
from services.email_service import send_email
from services.market_api import search_web

logger = logging.getLogger('StockMind-Scout')

class ScoutAgent:
    def __init__(self):
        self.groq_client = None
        self.gemini_model = None
        self._setup_llms()

    def _setup_llms(self):
        \"\"\"Initializes the LLM clients.\"\"\"
        if settings.GROQ_API_KEY:
            try:
                from groq import Groq
                self.groq_client = Groq(api_key=settings.GROQ_API_KEY)
            except Exception as e:
                logger.warning(f"Groq setup failed for Scout: {e}")
                
        if settings.GEMINI_API_KEY:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                self.gemini_model = genai.GenerativeModel('gemini-1.5-pro-latest')
            except Exception as e:
                logger.error(f"Gemini setup failed for Scout: {e}")

    def research_market(self, current_categories: list):
        \"\"\"
        Connected to live web search to scrape the latest trends 
        before generating a procurement proposal.
        \"\"\"
        logger.info(f"Initiating market research for categories: {current_categories}")
        
        # 1. Have the API actually search the live web first
        search_query = f"trending new technology products in {', '.join(current_categories)} {datetime.now().year}"
        live_web_data = search_web(search_query)
        
        # 2. Feed that live data into the LLM prompt
        prompt = f\"\"\"
        You are the Market Scout Agent for GIVA TECH LTD.
        Current Date: {datetime.now().strftime('%B %Y')}
        
        Here is LIVE data just pulled from the web regarding our current categories ({', '.join(current_categories)}):
        
        {live_web_data}
        
        Act as a proactive procurement officer. Based on this live data and your internal knowledge of global tech trends, 
        identify 3 BRAND NEW or highly trending products that we should add to our inventory.
        
        For each product, provide:
        1. Product Name & Brand
        2. Why it is trending (Market Justification)
        3. Estimated Supplier Cost vs Estimated Retail Price
        
        Format this as a professional business proposal.
        \"\"\"
        
        report_text = "Market research unavailable."
        
        # We prefer Gemini Pro here if available, as it has better broad world knowledge
        if self.gemini_model:
            try:
                response = self.gemini_model.generate_content(prompt)
                report_text = response.text
            except Exception as e:
                logger.error(f"Gemini research failed: {e}")
        elif self.groq_client:
            try:
                response = self.groq_client.chat.completions.create(
                    model='llama-3.3-70b-versatile',
                    messages=[{'role': 'user', 'content': prompt}],
                    max_tokens=1000,
                    temperature=0.7
                )
                report_text = response.choices[0].message.content
            except Exception as e:
                logger.error(f"Groq research failed: {e}")

        self._send_proposal(report_text)
        return report_text

    def _send_proposal(self, report_text: str):
        \"\"\"Emails the findings to the management team.\"\"\"
        subject = f"🌐 Market Scout Report - {datetime.now().strftime('%b %d, %Y')}"
        
        html_body = f\"\"\"
        <html><body style="font-family: Arial, sans-serif; background: #f4f4f5; color: #1f2937; padding: 20px;">
            <div style="max-width: 700px; margin: auto; background: #ffffff; padding: 30px; border-radius: 8px; border-top: 5px solid #3b82f6; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                <h2 style="color: #2563eb;">Market Scout: New Product Proposal</h2>
                <p style="color: #6b7280; font-size: 14px;">Autonomous Web Research completed on {datetime.now().strftime('%A, %B %d')}</p>
                <hr style="border-color: #e5e7eb; margin: 20px 0;">
                <div style="white-space: pre-wrap; line-height: 1.6;">
                    {report_text}
                </div>
                <hr style="border-color: #e5e7eb; margin: 20px 0;">
                <p style="font-size: 12px; color: #9ca3af; text-align: center;">StockMind AI - Procurement Division</p>
            </div>
        </body></html>
        \"\"\"
        
        send_email(subject, report_text, html_body, settings.ALERT_EMAIL)
        logger.info("Market Scout report emailed to management.")

# Global instance
scout_agent = ScoutAgent()
"""

filename = "agents/scout.py"

# Create the file in the Colab environment
with open(filename, "w") as file:
    file.write(scout_content)

print(f"✅ Successfully generated and upgraded {filename}.")
print("Initiating automatic download...")

# Trigger the browser to download the file
files.download(filename)