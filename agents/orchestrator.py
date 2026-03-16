import json
import logging
from core.config import settings
from core.database import load_inventory_from_db

logger = logging.getLogger('StockMind-Orchestrator')

class OrchestratorAgent:
    def __init__(self):
        self.groq_client = None
        self.gemini_model = None
        self._setup_llms()

    def _setup_llms(self):
        """Initializes the LLM clients with failover support."""
        if settings.GROQ_API_KEY:
            try:
                from groq import Groq
                self.groq_client = Groq(api_key=settings.GROQ_API_KEY)
                logger.info("Groq LLM connected for Orchestrator")
            except Exception as e:
                logger.warning(f"Groq setup failed: {e}")
                
        if settings.GEMINI_API_KEY:
            try:
                import google.generativeai as genai
                genai.configure(api_key=settings.GEMINI_API_KEY)
                # We enforce JSON output for the router to make it predictable
                self.gemini_model = genai.GenerativeModel(
                    'gemini-1.5-flash',
                    generation_config={"response_mime_type": "application/json"}
                )
                logger.info("Gemini LLM connected for Orchestrator")
            except Exception as e:
                logger.error(f"Gemini setup failed: {e}")

    def get_semantic_route(self, user_message: str) -> dict:
        """
        The Cognitive Brain: Decides WHICH agent should handle the request 
        and extracts key parameters from the user's natural language.
        """
        system_prompt = """
        You are the Routing Brain of StockMind AI, an enterprise inventory system.
        Analyze the user's request and route it to the correct specialized agent.
        
        Available Agents:
        - 'monitor': For checking stock levels, shortages, or physical inventory counts.
        - 'analyst': For revenue, margins, pricing, and financial performance.
        - 'advisor': For reorder quantities, purchase orders, and supplier communication.
        - 'scout': For market trends, competitor analysis, and finding new products.
        - 'reporter': For generating executive summaries or broad business overviews.

        Respond STRICTLY in valid JSON format:
        {
            "selected_agent": "agent_name",
            "confidence_score": 0.95,
            "extracted_parameters": {"category": "optional", "product_id": "optional"},
            "reasoning": "Brief explanation of why this agent was chosen"
        }
        """

        # 1. Try Groq First (Faster for routing)
        if self.groq_client:
            try:
                response = self.groq_client.chat.completions.create(
                    model='llama-3.3-70b-versatile',
                    messages=[
                        {'role': 'system', 'content': system_prompt},
                        {'role': 'user', 'content': user_message}
                    ],
                    response_format={"type": "json_object"},
                    max_tokens=200,
                    temperature=0.1 # Low temperature for logical consistency
                )
                return json.loads(response.choices[0].message.content)
            except Exception as e:
                logger.warning(f"Groq routing failed, falling back to Gemini: {e}")

        # 2. Fallback to Gemini
        if self.gemini_model:
            try:
                response = self.gemini_model.generate_content(
                    system_prompt + "\n\nUser Request: " + user_message
                )
                return json.loads(response.text)
            except Exception as e:
                logger.error(f"Gemini routing failed: {e}")
                
        # 3. Ultimate Fallback (If APIs are down)
        return {
            "selected_agent": "reporter", 
            "confidence_score": 0.0, 
            "extracted_parameters": {},
            "reasoning": "LLM APIs unavailable, defaulting to general reporter."
        }

    def process_chat(self, user_message: str):
        """
        The main entry point for a conversation.
        It routes the intent, loads context, and generates the final response.
        """
        # 1. Understand the intent
        route_data = self.get_semantic_route(user_message)
        agent_name = route_data.get("selected_agent", "reporter")
        logger.info(f"Routed request to: {agent_name.upper()} AGENT")

        # 2. Get live database context (RAG)
        # In the future, we will filter this using route_data['extracted_parameters']
        inventory = load_inventory_from_db()
        total_items = len(inventory)
        
        # 3. Generate Final Response
        # (For now, we build a simple response, but next we will split the actual 
        # agent personalities into their own files like monitor.py and analyst.py)
        
        execution_prompt = f"""
        You are the {agent_name.upper()} AGENT of StockMind AI.
        You have {total_items} items in the database. 
        User Request: {user_message}
        Extracted Context: {route_data.get('extracted_parameters')}
        
        Provide a professional, highly precise response based on your agent persona.
        ALWAYS respond in the SAME language the user writes in.
        """
        
        if self.groq_client:
            response = self.groq_client.chat.completions.create(
                model='llama-3.3-70b-versatile',
                messages=[{'role': 'system', 'content': execution_prompt}],
                max_tokens=800,
                temperature=0.6
            )
            final_text = response.choices[0].message.content
        else:
            # Strip JSON formatting requirement for the final conversational response
            standard_gemini = genai.GenerativeModel('gemini-1.5-flash')
            response = standard_gemini.generate_content(execution_prompt)
            final_text = response.text

        return {
            "response": final_text,
            "agent_used": agent_name.upper(),
            "debug_routing": route_data
        }

# Initialize a global instance to be imported by main.py
orchestrator = OrchestratorAgent()
