import logging
from typing import Dict, Any, List


class InternetMCP:
    PRIORITY_SITES = [
        "bandcamp.com",
        "soundcloud.com",
        "spotify.com",
        "reddit.com/r/music",
        "reddit.com/r/portugal",
        "reddit.com/r/leiria",
        "cm-leiria.pt",
        "regiaoleiria.pt",
        "publico.pt",
        "expresso.pt",
        "observador.pt",
        "musicaportugal.com",
        "blitz.pt",
        "agendalx.pt",
        "timeout.pt",
        "sapo.pt"
    ]

    def __init__(self, mcp_client=None):
        self.mcp_client = mcp_client
        self.logger = logging.getLogger(__name__)

    async def search_internet(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        try:
            priority_results = await self._search_priority_sites(query, max_results // 2)
            general_results = await self._general_search(query, max_results - len(priority_results))

            all_results = priority_results + general_results

            return {
                "success": True,
                "query": query,
                "results": all_results,
                "summary": self._create_summary(all_results)
            }

        except Exception as e:
            self.logger.error(f"Internet search failed: {e}")
            return {
                "success": False,
                "query": query,
                "results": [],
                "summary": "Search failed",
                "error": str(e)
            }

    async def _search_priority_sites(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        results = []

        for site in self.PRIORITY_SITES[:max_results]:
            try:
                site_query = f"site:{site} {query}"
                result = await self._perform_search(site_query, 1)
                if result:
                    results.extend(result)
                    if len(results) >= max_results:
                        break
            except:
                continue

        return results[:max_results]

    async def _general_search(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        try:
            return await self._perform_search(query, max_results)
        except:
            return []

    async def _perform_search(self, query: str, limit: int) -> List[Dict[str, Any]]:
        if self.mcp_client:
            result = await self.mcp_client.call_tool("web_search", {"query": query, "limit": limit})
            return self._parse_mcp_results(result)
        else:
            return await self._direct_api_search(query, limit)

    def _parse_mcp_results(self, mcp_result) -> List[Dict[str, Any]]:
        results = []
        try:
            if isinstance(mcp_result, dict) and "results" in mcp_result:
                for item in mcp_result["results"]:
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "snippet": item.get("snippet", ""),
                        "source": item.get("source", "")
                    })
        except Exception as e:
            self.logger.error(f"Error parsing MCP results: {e}")

        return results

    async def _direct_api_search(self, query: str, limit: int) -> List[Dict[str, Any]]:
        return []

    def _create_summary(self, results: List[Dict[str, Any]]) -> str:
        if not results:
            return "No results found"

        summary_parts = []
        for result in results[:3]:  # Top 3 results
            title = result.get("title", "")
            snippet = result.get("snippet", "")
            if title and snippet:
                summary_parts.append(f"{title}: {snippet}")

        return " | ".join(summary_parts)

    @staticmethod
    def get_tool_definition() -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "search_internet",
                "description": f"Search internet for current information. Prioritizes music sites: {', '.join(InternetMCP.PRIORITY_SITES[:6])}",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query (e.g. 'Taylor Swift latest album', 'Billboard top songs 2025')"
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results (default: 5)",
                            "default": 5
                        }
                    },
                    "required": ["query"]
                }
            }
        }