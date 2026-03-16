import logging
import json
import urllib.request
import urllib.parse
from core.self_healing import with_self_healing
from core.config import settings

logger = logging.getLogger('StockMind-MarketAPI')

@with_self_healing(fallback_return="Live market data currently unavailable due to search engine block. Relying on internal knowledge.")
def search_web(query: str, num_results: int = 3) -> str:
    """
    Performs a live web search to gather market intelligence.
    Currently uses a free, no-key DuckDuckGo HTML parser fallback.
    For production, replace this with SerpAPI or Google Custom Search.
    """
    logger.info(f"Scout Agent executing live web search for: '{query}'")
    
    # ---------------------------------------------------------
    # PREMIUM API TEMPLATE (e.g., SerpAPI / Tavily)
    # ---------------------------------------------------------
    # if settings.SERPAPI_KEY:
    #     url = f"https://serpapi.com/search.json?q={urllib.parse.quote(query)}&api_key={settings.SERPAPI_KEY}"
    #     response = urllib.request.urlopen(url)
    #     data = json.loads(response.read())
    #     results = [result['snippet'] for result in data.get('organic_results', [])[:num_results]]
    #     return " | ".join(results)
    
    # ---------------------------------------------------------
    # FREE FALLBACK (DuckDuckGo Lite)
    # ---------------------------------------------------------
    # We use a standard browser User-Agent so the search engine doesn't block the AI
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    
    req = urllib.request.Request(url, headers=headers)
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8')
            
            # Simple string parsing to extract snippets without needing heavy libraries like BeautifulSoup
            snippets = []
            parts = html.split('class="result__snippet')
            for part in parts[1:num_results + 1]:
                # Extract text between the tags
                snippet = part.split('>', 1)[1].split('</a>', 1)[0]
                # Clean up bold tags and HTML entities
                clean_snippet = snippet.replace('<b>', '').replace('</b>', '').replace('&#39;', "'").replace('&quot;', '"')
                snippets.append(clean_snippet.strip())
                
            if not snippets:
                return "No recent trends found on the web."
                
            compiled_research = "\n".join([f"- {s}" for s in snippets])
            logger.info("Successfully retrieved live web data.")
            return compiled_research
            
    except Exception as e:
        logger.error(f"Web search failed: {e}")
        raise e  # This triggers the @with_self_healing decorator to log the error and return the fallback!
