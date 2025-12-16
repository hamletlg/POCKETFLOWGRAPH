from .base import BasePlatformNode
from pocketflow import Node
import requests
from bs4 import BeautifulSoup
try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None

class WebSearchNode(BasePlatformNode, Node):
    NODE_TYPE = "web_search"
    DESCRIPTION = "Search the web using DuckDuckGo"
    PARAMS = {"query": "string", "max_results": "int"}
    
    def exec(self, prep_res):
        cfg = getattr(self, 'config', {})
        query = cfg.get("query", "")
        max_results = int(cfg.get("max_results", 5))
        
        # Use input as query if param is empty
        if not query and prep_res and isinstance(prep_res, str):
            query = prep_res
            
        if not query:
            return "Error: No query provided"
            
        if DDGS is None:
            return "Error: duckduckgo-search not installed"
            
        try:
            results = DDGS().text(query, max_results=max_results)
            # Format results
            formatted = ""
            for r in results:
                formatted += f"Title: {r['title']}\nLink: {r['href']}\nSnippet: {r['body']}\n\n"
            return formatted
        except Exception as e:
            return f"Search Error: {e}"

class WebFetchNode(BasePlatformNode, Node):
    NODE_TYPE = "web_fetch"
    DESCRIPTION = "Fetch text content from a URL"
    PARAMS = {"url": "string"}
    
    def exec(self, prep_res):
        cfg = getattr(self, 'config', {})
        url = cfg.get("url", "")
        
        if not url and prep_res and isinstance(prep_res, str):
            if prep_res.startswith("http"):
                url = prep_res
        
        if not url:
            return "Error: No URL provided"
            
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Simple text extraction
            # Remove scripts and styles
            for script in soup(["script", "style"]):
                script.decompose()
                
            text = soup.get_text()
            # Clean lines
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            
            return text[:10000] # Limit size
            
        except Exception as e:
            return f"Fetch Error: {e}"

import feedparser

class RSSNode(BasePlatformNode, Node):
    NODE_TYPE = "rss_read"
    DESCRIPTION = "Fetch entries from an RSS feed"
    PARAMS = {"url": "string", "max_entries": "int"}
    
    def exec(self, prep_res):
        cfg = getattr(self, 'config', {})
        url = cfg.get("url", "")
        max_entries = int(cfg.get("max_entries", 5))
        
        # Use input as URL if param is empty
        if not url and prep_res and isinstance(prep_res, str):
             if prep_res.startswith("http"):
                url = prep_res
        
        if not url:
            return "Error: No RSS URL provided"
            
        try:
            feed = feedparser.parse(url)
            if feed.bozo:
                 return f"Error parsing feed: {feed.bozo_exception}"
                 
            entries = feed.entries[:max_entries]
            formatted = f"Feed Title: {feed.feed.get('title', 'Unknown')}\n\n"
            
            for entry in entries:
                formatted += f"Title: {entry.get('title', 'No Title')}\n"
                formatted += f"Link: {entry.get('link', '#')}\n"
                formatted += f"Summary: {entry.get('summary', 'No Summary')}\n"
                formatted += "---\n"
                
            return formatted
        except Exception as e:
            return f"RSS Error: {e}"
