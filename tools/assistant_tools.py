import logging
from typing import Dict, Any, List

class AssistantTools:
    def __init__(self, internet_mcp, config=None):
        self.internet = internet_mcp
        self.config = config or {}
        self.logger = logging.getLogger(__name__)

    async def search_web(self, query: str, max_results: int = 3) -> dict:
        try:
            results = await self.internet.search_internet(
                query=query,
                max_results=max_results
            )
            if results.get("success"):
                return {
                    "status": "success",
                    "results": results.get("results", [])[:max_results]
                }
            return {"status": "error", "message": "Search failed"}
        except Exception as e:
            self.logger.error(f"Web search error: {e}")
            return {"status": "error", "message": str(e)}

    @staticmethod
    def get_tool_definitions():
        return [
            {
                "type": "function",
                "function": {
                    "name": "search_web",
                    "description": "Search the web for current information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "max_results": {
                                "type": "integer",
                                "minimum": 1,
                                "maximum": 5
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        ]
