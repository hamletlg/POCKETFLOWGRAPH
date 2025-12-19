import os
from .base import BasePlatformNode
from pocketflow import Node
from config import ROOT_DIR


class FileReadNode(BasePlatformNode, Node):
    NODE_TYPE = "file_read"
    DESCRIPTION = "Read content from a file"
    PARAMS = {"path": "string"}

    def prep(self, shared):
        cfg = getattr(self, "config", {})
        return {"path": cfg.get("path", "")}

    def exec(self, prep_res):
        path = prep_res.get("path", "")
        if not path:
            return "Error: No path provided"

        try:
            path = ROOT_DIR / path
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {e}"


class FileWriteNode(BasePlatformNode, Node):
    NODE_TYPE = "file_write"
    DESCRIPTION = "Write content to a file"
    PARAMS = {
        "path": {"type": "string", "description": "File path to write to"},
        "content": {
            "type": "string",
            "description": "Content to write (optional, uses previous node output if empty)",
        },
        "mode": {
            "type": "string",
            "enum": ["w", "a"],
            "default": "w",
            "description": "Write mode: 'w' (overwrite) or 'a' (append)",
        },
    }

    def prep(self, shared):
        cfg = getattr(self, "config", {})

        # Get input from previous node (PocketFlow convention)
        input_data = None
        results = shared.get("results", {})
        if results:
            # Get the last result added to shared
            last_key = list(results.keys())[-1]
            input_data = results[last_key]

        return {
            "path": cfg.get("path", ""),
            "mode": cfg.get("mode", "w"),
            "content_param": cfg.get("content", ""),
            "input_data": input_data,
        }

    def exec(self, prep_res):
        path = prep_res.get("path", "")
        mode = prep_res.get("mode", "w")
        content_param = prep_res.get("content_param", "")
        input_data = prep_res.get("input_data")

        # Prioritize input_data if it exists, otherwise use content_param
        content_to_write = input_data if input_data is not None else content_param

        if not path:
            return "Error: No path provided"

        try:
            # Handle non-string data
            if not isinstance(content_to_write, str):
                import json

                try:
                    content_to_write = json.dumps(content_to_write, indent=2)
                except:
                    content_to_write = str(content_to_write)

            path = ROOT_DIR / path
            with open(path, mode, encoding="utf-8") as f:
                f.write(content_to_write)
            return f"Successfully wrote to {path}"
        except Exception as e:
            return f"Error writing file: {e}"


class PDFReadNode(BasePlatformNode, Node):
    """
    Read PDF file(s) and return list for use with Loop node.

    - Single file: Returns list of page texts
    - Folder: Returns list of PDF file paths (loop over these, then read each)
    """

    NODE_TYPE = "pdf_read"
    DESCRIPTION = "Read PDF (file returns pages, folder returns file list)"
    PARAMS = {
        "path": {"type": "string", "description": "Path to PDF file OR folder"},
        "page_range": {
            "type": "string",
            "description": "For files: '1-5' or '1,3,5' or empty for all pages",
        },
        "recursive": {
            "type": "boolean",
            "default": False,
            "description": "For folders: search subfolders too",
        },
    }

    def prep(self, shared):
        cfg = getattr(self, "config", {})
        return {
            "path": cfg.get("path", ""),
            "page_range": cfg.get("page_range", ""),
            "recursive": cfg.get("recursive", False),
        }

    def exec(self, prep_res):
        import glob

        path = prep_res.get("path", "")
        page_range = prep_res.get("page_range", "")
        recursive = prep_res.get("recursive", False)

        if not path:
            return {"error": "No path provided", "items": [], "mode": "error"}

        if not os.path.exists(path):
            return {"error": f"Path not found: {path}", "items": [], "mode": "error"}

        # FOLDER MODE: Return list of PDF file paths
        if os.path.isdir(path):
            return self._read_folder(path, recursive)

        # FILE MODE: Return list of page texts
        return self._read_file(path, page_range)

    def _read_folder(self, folder_path: str, recursive: bool) -> dict:
        """Find all PDFs in folder, return list of file paths."""
        import glob

        if recursive:
            pattern = os.path.join(folder_path, "**", "*.pdf")
            pdf_files = glob.glob(pattern, recursive=True)
        else:
            pattern = os.path.join(folder_path, "*.pdf")
            pdf_files = glob.glob(pattern)

        # Sort for consistent ordering
        pdf_files = sorted(pdf_files)

        return {
            "items": pdf_files,
            "count": len(pdf_files),
            "mode": "folder",
            "path": folder_path,
        }

    def _read_file(self, file_path: str, page_range: str) -> dict:
        """Read single PDF, return list of page texts."""
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(file_path)
            total_pages = len(doc)

            # Parse page range
            pages_to_read = self._parse_page_range(page_range, total_pages)

            # Extract text from each page
            page_texts = []
            for page_num in pages_to_read:
                page = doc[page_num]
                text = page.get_text()
                page_texts.append(text)

            doc.close()

            return {
                "items": page_texts,
                "total_pages": total_pages,
                "pages_read": len(page_texts),
                "mode": "file",
                "path": file_path,
            }

        except Exception as e:
            return {"error": f"Error reading PDF: {e}", "items": [], "mode": "error"}

    def _parse_page_range(self, page_range: str, total_pages: int) -> list:
        """Parse page range string like '1-5' or '1,3,5' into list of 0-indexed page numbers."""
        if not page_range.strip():
            return list(range(total_pages))

        pages = set()
        parts = page_range.replace(" ", "").split(",")

        for part in parts:
            if "-" in part:
                try:
                    start, end = part.split("-")
                    start = max(1, int(start))
                    end = min(total_pages, int(end))
                    pages.update(range(start - 1, end))
                except ValueError:
                    pass
            else:
                try:
                    page = int(part)
                    if 1 <= page <= total_pages:
                        pages.add(page - 1)
                except ValueError:
                    pass

        return sorted(pages) if pages else list(range(total_pages))

    def post(self, shared, prep_res, exec_res):
        """Store result for Loop node compatibility."""
        if "memory" not in shared:
            shared["memory"] = {}

        mode = exec_res.get("mode", "error")

        if mode == "folder":
            # Folder mode: store file list metadata
            shared["memory"]["pdf_folder"] = exec_res.get("path", "")
            shared["memory"]["pdf_file_count"] = exec_res.get("count", 0)
        elif mode == "file":
            # File mode: store page metadata
            shared["memory"]["pdf_path"] = exec_res.get("path", "")
            shared["memory"]["pdf_total_pages"] = exec_res.get("total_pages", 0)
            shared["memory"]["pdf_pages_read"] = exec_res.get("pages_read", 0)

        # Return the list (file paths or page texts) for Loop compatibility
        items = exec_res.get("items", [])

        if exec_res.get("error"):
            super().post(shared, prep_res, exec_res.get("error"))
        else:
            super().post(shared, prep_res, items)

        return None
