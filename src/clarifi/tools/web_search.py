"""Web search tool — lets the agent look up public information.

Uses DuckDuckGo (no API key needed) to search for company info,
CUI lookups, legal status, addresses, etc.
"""

import logging

from langchain_core.tools import tool

logger = logging.getLogger(__name__)


@tool
async def web_search(query: str, max_results: int = 5) -> dict:
    """Cauta informatii publice pe internet (DuckDuckGo).

    Foloseste pentru:
    - Informatii despre companii (CUI, adresa, stare ANAF)
    - Verificare firme (activa/inactiva, insolventa)
    - Informatii generale necesare pentru analiza

    Args:
        query — ce cauti (ex: "RO12345678 ANAF", "SC Exemplu SRL insolventa")
        max_results — cate rezultate (default 5)
    """
    try:
        from duckduckgo_search import DDGS

        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=max_results):
                results.append({
                    "title": r.get("title", ""),
                    "snippet": r.get("body", ""),
                    "url": r.get("href", ""),
                })

        if not results:
            return {"query": query, "results": [], "message": "Niciun rezultat gasit"}

        return {"query": query, "results": results}

    except ImportError:
        logger.warning("duckduckgo-search not installed")
        return {
            "query": query,
            "error": "Cautarea web nu este disponibila (duckduckgo-search nu e instalat)",
        }
    except Exception as e:
        logger.warning("Web search failed: %s", e)
        return {"query": query, "error": str(e)}
