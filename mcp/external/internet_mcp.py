import logging
from urllib.parse import quote_plus
from typing import Dict, Any, List
import aiohttp
from core.config import get_tool_config


class InternetMCP:

    def __init__(self, mcp_client=None, config=None, default_engine: str = "Brave"):
        self.mcp_client = mcp_client
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self.default_engine = default_engine if default_engine in ["Brave", "Perplexity"] else "Brave"
        self.logger.info(f"InternetMCP initialized with default engine: {self.default_engine}")

    async def search_internet(self, query: str, max_results: int = 5, engine: str | None = None) -> Dict[str, Any]:
        try:
            self.logger.info(f" -----> : internet.search q='{query}' max={max_results}")
            count = max_results if max_results > 0 else 0
            self.logger.info(f"internet.search engine param received: {engine}")
            eng = (engine or getattr(self, 'default_engine', 'Brave')).upper()
            self.logger.info(f"internet.search using engine: {eng}")
            if eng == "PERPLEXITY":
                pdata = await self.ask_perplexity(query, max_items=count or 0)
                items = pdata.get("items", []) if isinstance(pdata, dict) else []
                all_results = []
                for s in items[:count]:
                    all_results.append({
                        "title": "",
                        "url": "",
                        "snippet": s,
                        "source": "perplexity"
                    })
            else:
                all_results = await self._brave_search(query, count)
            self.logger.info(f"internet.search returning general results={len(all_results)}, search engine={eng}")
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

    async def _brave_search(self, query: str, limit: int) -> List[Dict[str, Any]]:
        tool_cfg = self._get_tool_config()
        api_key = tool_cfg.get("brave_api_key", "")
        url = f"https://api.search.brave.com/res/v1/web/search?q={quote_plus(query)}&count={limit}"
        results: List[Dict[str, Any]] = []
        try:
            self.logger.info(f"internet.brave url='{url}' limit={limit}")
            headers = {"X-Subscription-Token": api_key}
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=30) as resp:
                    data = await resp.json()
            web = data.get("rest", {}) if isinstance(data, dict) else {}
            items = web.get("results", []) if isinstance(web, dict) else []
            self.logger.info(f"internet.brave items_found={len(items)}")
            for item in items[:limit]:
                title = item.get("title", "")
                link = item.get("url", "")
                snippet = item.get("description", "")
                results.append({
                    "title": title,
                    "url": link,
                    "snippet": snippet,
                    "source": "brave"
                })
        except Exception as e:
            self.logger.error(f"Brave search failed: {e}")
        self.logger.info(f"internet.brave results={len(results)}")
        return results

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
    def get_tool_definition(default_engine: str = "Brave") -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "search_internet",
                "description": "Search internet for current information.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Search query"
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results",
                            "default": 5
                        },
                        "engine": {
                            "type": "string",
                            "description": "Search engine to use",
                            "enum": ["Brave", "Perplexity"],
                            "default": default_engine
                        }
                    },
                    "required": ["query"]
                }
            }
        }

    async def _perplexity_chat(self, question: str) -> Dict[str, Any]:
        tool_cfg = self._get_tool_config()
        api_key = tool_cfg.get("perplexity_api_key", "")
        if not api_key:
            return {}
        url = "https://api.perplexity.ai/chat/completions"
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json",
                   "accept": "application/json"}
        payload = {
            "model": "sonar",
            "messages": [
                {"role": "system", "content": "Respond concisely."},
                {"role": "user", "content": question}
            ]
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload, timeout=30) as resp:
                    data = await resp.json()
            return data if isinstance(data, dict) else {}
        except Exception as e:
            self.logger.error(f"Perplexity chat failed: {e}")
            return {}

    async def ask_perplexity(self, prompt: str, max_items: int = 3) -> Dict[str, Any]:
        data = await self._perplexity_chat(prompt)
        content = ""
        try:
            choices = data.get("choices", []) if isinstance(data, dict) else []
            if choices:
                msg = choices[0].get("message", {})
                content = msg.get("content", "") or ""
        except Exception:
            content = ""
        items: List[str] = []
        if content:
            txt = content.strip()
            if "," in txt and "\n" not in txt:
                parts = [p.strip() for p in txt.split(",") if p.strip()]
            else:
                parts = [p.strip(" -•\t").strip() for p in txt.splitlines() if p.strip()]
            for p in parts:
                if p and len(items) < max_items:
                    items.append(p)
        while len(items) < max_items:
            items.append("")
        return {"items": items[:max_items]}

    def _get_tool_config(self):
        if not self.config:
            self.logger.warning("No config provided to InternetMCP")
            return {}

        tool_cfg = get_tool_config(self.config, "internet_mcp")
        if tool_cfg is None:
            if not hasattr(self, '_config_warning_logged'):
                self.logger.warning("internet_mcp configuration not found - using empty config")
                self._config_warning_logged = True
            return {}

        if not hasattr(self, '_config_loaded_logged'):
            brave_key = tool_cfg.get("brave_api_key", "")
            perplexity_key = tool_cfg.get("perplexity_api_key", "")
            self.logger.info(
                f"internet_mcp config loaded: brave_key={'present' if brave_key else 'missing'}, perplexity_key={'present' if perplexity_key else 'missing'}")
            self._config_loaded_logged = True

        return tool_cfg
