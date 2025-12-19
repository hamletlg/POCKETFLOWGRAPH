import os
import json
import chromadb
import openai
from .base import BasePlatformNode
from pocketflow import Node


class VectorMemoryNode(BasePlatformNode, Node):
    """
    Vector search memory using ChromaDB for RAG and episodic memory.

    Operations:
    - add: Store text and metadata with automatic embeddings
    - query: Vector search for relevant technical content
    - delete: Remove a collection or items
    - list: List all available collections
    """

    NODE_TYPE = "vector_memory"
    DESCRIPTION = "Semantic search memory (RAG) using ChromaDB"
    PARAMS = {
        "operation": {
            "type": "string",
            "enum": ["add", "query", "delete", "list"],
            "default": "add",
            "description": "Vector memory operation",
        },
        "collection": {
            "type": "string",
            "default": "main",
            "description": "Collection name",
        },
        "text": {"type": "string", "description": "Text to add or search query"},
        "metadata": {
            "type": "string",
            "description": "JSON metadata for 'add' operation",
        },
        "top_k": {
            "type": "int",
            "default": 3,
            "description": "Number of results for 'query' operation",
        },
        "api_base": {
            "type": "string",
            "description": "Embeddings API base URL (optional)",
        },
        "model": {
            "type": "string",
            "default": "text-embedding-3-small",
            "description": "Embedding model name",
        },
    }

    CHROMA_PATH = "backend/.chroma_db"

    def prep(self, shared):
        cfg = getattr(self, "config", {})

        # Determine API base for embeddings
        default_base = shared.get("llm_base_url", "http://localhost:1234/v1")
        api_base = cfg.get("api_base") or default_base

        # Get input data if text param is empty
        input_text = ""
        results = shared.get("results", {})
        if results:
            last_key = list(results.keys())[-1]
            input_text = str(results[last_key])

        return {
            "operation": cfg.get("operation", "query").lower().strip(),
            "collection": cfg.get("collection", "main").strip(),
            "text": cfg.get("text") or input_text,
            "metadata": cfg.get("metadata", "{}"),
            "top_k": int(cfg.get("top_k", 3)),
            "api_base": api_base,
            "model": cfg.get("model", "text-embedding-3-small"),
            "shared": shared,
        }

    def exec(self, prep_res):
        op = prep_res["operation"]
        col_name = prep_res["collection"]
        text = prep_res["text"]
        metadata_str = prep_res["metadata"]
        top_k = prep_res["top_k"]
        api_base = prep_res["api_base"]
        model = prep_res["model"]

        os.makedirs(self.CHROMA_PATH, exist_ok=True)
        client = chromadb.PersistentClient(path=self.CHROMA_PATH)

        # Define embedding function using OpenAI-compatible API
        class OpenAIEmbeddingFunction(chromadb.EmbeddingFunction):
            def __init__(self, base_url, model_name):
                self.client = openai.OpenAI(base_url=base_url, api_key="dummy")
                self.model = model_name

            def __call__(self, input):
                # Ensure input is a list of strings
                if isinstance(input, str):
                    input = [input]

                try:
                    response = self.client.embeddings.create(
                        input=input, model=self.model
                    )
                    return [e.embedding for e in response.data]
                except Exception as e:
                    print(f"Embedding Error: {e}")
                    raise e

        # Initialize embedding function
        embedding_function = None
        if api_base:
            embedding_function = OpenAIEmbeddingFunction(api_base, model)

        try:
            if op == "add":
                if not text:
                    return {"success": False, "message": "No text provided to add"}

                collection = client.get_or_create_collection(
                    name=col_name, embedding_function=embedding_function
                )

                # Parse metadata
                metadata = {}
                try:
                    metadata = json.loads(metadata_str)
                except:
                    pass

                # Use a simple hash or UUID for ID
                import uuid

                doc_id = str(uuid.uuid4())

                collection.add(documents=[text], metadatas=[metadata], ids=[doc_id])
                return {
                    "success": True,
                    "message": f"Added to '{col_name}'",
                    "id": doc_id,
                }

            elif op == "query":
                if not text:
                    return {"success": False, "message": "No query text provided"}

                try:
                    collection = client.get_collection(
                        name=col_name, embedding_function=embedding_function
                    )
                except Exception:
                    return {
                        "success": False,
                        "message": f"Collection '{col_name}' not found",
                    }

                results = collection.query(query_texts=[text], n_results=top_k)

                # Format results for easier use
                formatted_results = []
                for i in range(len(results["documents"][0])):
                    formatted_results.append(
                        {
                            "document": results["documents"][0][i],
                            "metadata": results["metadatas"][0][i],
                            "distance": results["distances"][0][i]
                            if "distances" in results
                            else None,
                        }
                    )

                return {"success": True, "results": formatted_results}

            elif op == "delete":
                client.delete_collection(name=col_name)
                return {"success": True, "message": f"Deleted collection '{col_name}'"}

            elif op == "list":
                cols = client.list_collections()
                return {"success": True, "collections": [c.name for c in cols]}

            else:
                return {"success": False, "message": f"Unknown operation: {op}"}

        except Exception as e:
            import traceback

            traceback.print_exc()
            return {"success": False, "error": str(e)}

    def post(self, shared, prep_res, exec_res):
        # We prefer to return the results list if it's a query
        if prep_res["operation"] == "query" and exec_res.get("success"):
            # If we want to return just the text of the top result for easy chaining:
            if exec_res.get("results"):
                top_doc = exec_res["results"][0]["document"]
                super().post(shared, prep_res, top_doc)
                # Also store the full structured results in a specific key
                shared["memory"]["last_vector_query"] = exec_res["results"]
            else:
                super().post(shared, prep_res, "No results found")
        else:
            super().post(shared, prep_res, exec_res)

        return None
