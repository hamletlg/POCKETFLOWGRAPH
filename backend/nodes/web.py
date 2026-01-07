from .base import BasePlatformNode
from pocketflow import Node
import requests
from bs4 import BeautifulSoup

try:
    from tavily import TavilyClient
except ImportError:
    TavilyClient = None


class WebSearchNode(BasePlatformNode, Node):
    """Search the web using Tavily with variable substitution and structured output."""

    NODE_TYPE = "web_search"
    DESCRIPTION = "Search web using Tavily (supports {input}, {memory_key})"
    PARAMS = {
        "query": {
            "type": "string",
            "description": "Search query (supports {input}, {memory_key})",
        },
        "api_key": {
            "type": "string",
            "description": "Tavily API Key (optional if TAVILY_API_KEY env var is set)",
        },
        "max_results": {
            "type": "int",
            "default": 5,
            "description": "Maximum number of results to return",
        },
        "search_depth": {
             "type": "string",
             "enum": ["basic", "advanced"],
             "default": "basic",
             "description": "Search depth: 'basic' or 'advanced'",
        },
        "as_list": {
            "type": "boolean",
            "default": False,
            "description": "Return results as list for Loop compatibility",
        },
    }

    def prep(self, shared):
        cfg = getattr(self, "config", {})

        # Build context for variable substitution
        context = {}
        results = shared.get("results", {})
        if results:
            last_key = list(results.keys())[-1]
            context["input"] = results[last_key]

        if "memory" in shared:
            context.update(shared["memory"])

        return {
            "query": cfg.get("query", ""),
            "api_key": cfg.get("api_key", ""),
            "max_results": int(cfg.get("max_results", 5) or 5),
            "search_depth": cfg.get("search_depth", "basic"),
            "as_list": cfg.get("as_list", False),
            "context": context,
        }

    def exec(self, prep_res):
        query = prep_res["query"]
        api_key = prep_res["api_key"] or None  # Allow None to pick up env var
        max_results = prep_res["max_results"]
        search_depth = prep_res["search_depth"]
        as_list = prep_res["as_list"]
        context = prep_res["context"]

        # Variable substitution
        for key, value in context.items():
            query = query.replace(f"{{{key}}}", str(value))

        # Use input as query if param is empty
        if not query and "input" in context:
            query = str(context["input"])

        if not query:
            return {"error": "No query provided", "results": []}

        if TavilyClient is None:
             return {"error": "tavily-python not installed", "results": []}

        try:
            # Initialize client; let it try to find env var if api_key is None/Empty
            # Note: TavilyClient might raise error if no key found even with env var mechanism, 
            # depending on version, but usually it checks environment.
            # To be safe, we can check os.environ or just pass it if we have it.
            # If prep_res["api_key"] is "", we should pass None or let library handle it.
            # Best practice: if not provided in config, use None so library looks for TAVILY_API_KEY.
            
            # The library usually expects api_key arg.
            import os
            if not api_key:
                api_key = os.environ.get("TAVILY_API_KEY")
            
            if not api_key:
                 return {"error": "Missing Tavily API Key", "results": []}

            client = TavilyClient(api_key=api_key)
            
            response = client.search(
                query=query,
                search_depth=search_depth,
                max_results=max_results
            )
            
            # Tavily returns a dict with 'results' list
            raw_results = response.get("results", [])

            # Structure results
            results = []
            for r in raw_results:
                results.append(
                    {
                        "title": r.get("title", ""),
                        "url": r.get("url", ""),
                        "snippet": r.get("content", ""),
                    }
                )

            if as_list:
                return {"results": results, "count": len(results), "query": query}
            else:
                # Format as text for backward compatibility
                formatted = ""
                for r in results:
                    formatted += f"Title: {r['title']}\nLink: {r['url']}\nSnippet: {r['snippet']}\n\n"
                return {
                    "text": formatted,
                    "results": results,
                    "count": len(results),
                    "query": query,
                }

        except Exception as e:
            return {"error": str(e), "results": []}

    def post(self, shared, prep_res, exec_res):
        if prep_res["as_list"]:
            super().post(shared, prep_res, exec_res.get("results", []))
        else:
            super().post(
                shared, prep_res, exec_res.get("text", exec_res.get("error", ""))
            )
        return None


class WebFetchNode(BasePlatformNode, Node):
    """Fetch web content with variable substitution and configurable options."""

    NODE_TYPE = "web_fetch"
    DESCRIPTION = "Fetch text from URL (supports {input}, {memory_key})"
    PARAMS = {
        "url": {
            "type": "string",
            "description": "URL to fetch (supports {input}, {memory_key})",
        },
        "max_chars": {
            "type": "int",
            "default": 10000,
            "description": "Maximum characters to return (0 for unlimited)",
        },
        "extract_links": {
            "type": "boolean",
            "default": False,
            "description": "Also extract links from the page",
        },
    }

    DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    def prep(self, shared):
        cfg = getattr(self, "config", {})

        # Build context
        context = {}
        results = shared.get("results", {})
        if results:
            last_key = list(results.keys())[-1]
            context["input"] = results[last_key]

        if "memory" in shared:
            context.update(shared["memory"])

        return {
            "url": cfg.get("url", ""),
            "max_chars": int(cfg.get("max_chars", 10000) or 10000),
            "extract_links": cfg.get("extract_links", False),
            "context": context,
        }

    def exec(self, prep_res):
        url = prep_res["url"]
        max_chars = prep_res["max_chars"]
        extract_links = prep_res["extract_links"]
        context = prep_res["context"]

        # Variable substitution
        for key, value in context.items():
            url = url.replace(f"{{{key}}}", str(value))

        # Use input as URL if param is empty
        if not url and "input" in context:
            input_val = str(context["input"])
            if input_val.startswith("http"):
                url = input_val

        if not url:
            return {"error": "No URL provided", "text": ""}

        try:
            headers = {"User-Agent": self.DEFAULT_USER_AGENT}
            resp = requests.get(url, timeout=15, headers=headers)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, "html.parser")

            # Extract links if requested
            links = []
            if extract_links:
                for a in soup.find_all("a", href=True):
                    href = a["href"]
                    if href.startswith("http"):
                        links.append({"text": a.get_text(strip=True), "url": href})

            # Remove scripts and styles
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()

            text = soup.get_text()
            # Clean lines
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = "\n".join(chunk for chunk in chunks if chunk)

            # Apply limit
            if max_chars > 0 and len(text) > max_chars:
                text = text[:max_chars] + "..."

            return {"text": text, "links": links, "url": url, "length": len(text)}

        except Exception as e:
            return {"error": str(e), "text": "", "url": url}

    def post(self, shared, prep_res, exec_res):
        if exec_res.get("error"):
            super().post(shared, prep_res, exec_res["error"])
        else:
            super().post(shared, prep_res, exec_res.get("text", ""))
        return None


import feedparser


class RSSNode(BasePlatformNode, Node):
    """Fetch RSS feed with Loop-compatible output."""

    NODE_TYPE = "rss_read"
    DESCRIPTION = "Fetch RSS feed entries (supports {input}, as_list for Loop)"
    PARAMS = {
        "url": {
            "type": "string",
            "description": "RSS feed URL (supports {input}, {memory_key})",
        },
        "max_entries": {
            "type": "int",
            "default": 10,
            "description": "Maximum number of entries to return",
        },
        "as_list": {
            "type": "boolean",
            "default": False,
            "description": "Return entries as list for Loop compatibility",
        },
    }

    def prep(self, shared):
        cfg = getattr(self, "config", {})

        # Build context
        context = {}
        results = shared.get("results", {})
        if results:
            last_key = list(results.keys())[-1]
            context["input"] = results[last_key]

        if "memory" in shared:
            context.update(shared["memory"])

        return {
            "url": cfg.get("url", ""),
            "max_entries": int(cfg.get("max_entries", 5) or 5),
            "as_list": cfg.get("as_list", False),
            "context": context,
        }

    def exec(self, prep_res):
        url = prep_res["url"]
        max_entries = prep_res["max_entries"]
        as_list = prep_res["as_list"]
        context = prep_res["context"]

        # Variable substitution
        for key, value in context.items():
            url = url.replace(f"{{{key}}}", str(value))

        # Use input as URL if param is empty
        if not url and "input" in context:
            input_val = str(context["input"])
            if input_val.startswith("http"):
                url = input_val

        if not url:
            return {"error": "No RSS URL provided", "entries": []}

        try:
            feed = feedparser.parse(url)
            if feed.bozo and not feed.entries:
                return {
                    "error": f"Error parsing feed: {feed.bozo_exception}",
                    "entries": [],
                }

            entries = []
            for entry in feed.entries[:max_entries]:
                entries.append(
                    {
                        "title": entry.get("title", "No Title"),
                        "link": entry.get("link", ""),
                        "summary": entry.get("summary", ""),
                        "published": entry.get("published", ""),
                    }
                )

            feed_info = {
                "title": feed.feed.get("title", "Unknown"),
                "link": feed.feed.get("link", ""),
                "entries": entries,
                "count": len(entries),
            }

            if not as_list:
                # Format as text for backward compatibility
                formatted = f"Feed: {feed_info['title']}\n\n"
                for e in entries:
                    formatted += f"Title: {e['title']}\nLink: {e['link']}\nSummary: {e['summary']}\n---\n"
                feed_info["text"] = formatted

            return feed_info

        except Exception as e:
            return {"error": str(e), "entries": []}

    def post(self, shared, prep_res, exec_res):
        if prep_res["as_list"]:
            super().post(shared, prep_res, exec_res.get("entries", []))
        else:
            super().post(
                shared, prep_res, exec_res.get("text", exec_res.get("error", ""))
            )
        return None
