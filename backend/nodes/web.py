from .base import BasePlatformNode
from pocketflow import Node
import requests
from bs4 import BeautifulSoup
try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None


class WebSearchNode(BasePlatformNode, Node):
    """Search the web with variable substitution and structured output."""
    NODE_TYPE = "web_search"
    DESCRIPTION = "Search web using DuckDuckGo (supports {input}, {memory_key})"
    PARAMS = {
        "query": "string",
        "max_results": "int",
        "as_list": "boolean"  # Return as list for Loop compatibility
    }

    def prep(self, shared):
        cfg = getattr(self, 'config', {})
        
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
            "max_results": int(cfg.get("max_results", 5) or 5),
            "as_list": cfg.get("as_list", False),
            "context": context
        }

    def exec(self, prep_res):
        query = prep_res["query"]
        max_results = prep_res["max_results"]
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
        
        if DDGS is None:
            return {"error": "duckduckgo-search not installed", "results": []}
        
        try:
            raw_results = DDGS().text(query, max_results=max_results)
            
            # Structure results
            results = []
            for r in raw_results:
                results.append({
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", "")
                })
            
            if as_list:
                return {"results": results, "count": len(results), "query": query}
            else:
                # Format as text for backward compatibility
                formatted = ""
                for r in results:
                    formatted += f"Title: {r['title']}\nLink: {r['url']}\nSnippet: {r['snippet']}\n\n"
                return {"text": formatted, "results": results, "count": len(results), "query": query}
                
        except Exception as e:
            return {"error": str(e), "results": []}

    def post(self, shared, prep_res, exec_res):
        if prep_res["as_list"]:
            super().post(shared, prep_res, exec_res.get("results", []))
        else:
            super().post(shared, prep_res, exec_res.get("text", exec_res.get("error", "")))
        return None


class WebFetchNode(BasePlatformNode, Node):
    """Fetch web content with variable substitution and configurable options."""
    NODE_TYPE = "web_fetch"
    DESCRIPTION = "Fetch text from URL (supports {input}, {memory_key})"
    PARAMS = {
        "url": "string",
        "max_chars": "int",      # Default 10000, 0 for unlimited
        "extract_links": "boolean"  # Also extract links
    }
    
    DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

    def prep(self, shared):
        cfg = getattr(self, 'config', {})
        
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
            "context": context
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
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Extract links if requested
            links = []
            if extract_links:
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    if href.startswith('http'):
                        links.append({"text": a.get_text(strip=True), "url": href})
            
            # Remove scripts and styles
            for script in soup(["script", "style", "nav", "footer", "header"]):
                script.decompose()
            
            text = soup.get_text()
            # Clean lines
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
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
        "url": "string",
        "max_entries": "int",
        "as_list": "boolean"  # Return as list for Loop compatibility
    }

    def prep(self, shared):
        cfg = getattr(self, 'config', {})
        
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
            "context": context
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
                return {"error": f"Error parsing feed: {feed.bozo_exception}", "entries": []}
            
            entries = []
            for entry in feed.entries[:max_entries]:
                entries.append({
                    "title": entry.get("title", "No Title"),
                    "link": entry.get("link", ""),
                    "summary": entry.get("summary", ""),
                    "published": entry.get("published", "")
                })
            
            feed_info = {
                "title": feed.feed.get("title", "Unknown"),
                "link": feed.feed.get("link", ""),
                "entries": entries,
                "count": len(entries)
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
            super().post(shared, prep_res, exec_res.get("text", exec_res.get("error", "")))
        return None

