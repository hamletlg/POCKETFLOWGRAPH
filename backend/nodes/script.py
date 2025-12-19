import subprocess
import os
import json
import tempfile
from .base import BasePlatformNode
from pocketflow import Node


class ScriptNode(BasePlatformNode, Node):
    """
    Execute external Bash commands or Python scripts.

    Features:
    - Supports Bash and Python 3.
    - Input via stdin or POCKETFLOW_INPUT environment variable.
    - Return stdout, exit code, or a full result object.
    """

    NODE_TYPE = "script"
    DESCRIPTION = "Execute external Bash or Python code"
    PARAMS = {
        "interpreter": {
            "type": "string",
            "enum": ["bash", "python"],
            "default": "bash",
            "description": "Script interpreter to use",
        },
        "script_body": {"type": "string", "description": "The script code to execute"},
        "input_mode": {
            "type": "string",
            "enum": ["none", "stdin", "env"],
            "default": "stdin",
            "description": "How to pass input to the script",
        },
        "return_type": {
            "type": "string",
            "enum": ["stdout", "exit_code", "json"],
            "default": "stdout",
            "description": "What the script returns",
        },
    }

    def prep(self, shared):
        cfg = getattr(self, "config", {})

        # Get input from previous node (standard PocketFlow pattern)
        results = shared.get("results", {})
        last_result = ""
        if results:
            last_key = list(results.keys())[-1]
            last_result = results[last_key]

        # Ensure last_result is a string for stdin/env
        if not isinstance(last_result, str):
            try:
                last_result = json.dumps(last_result, ensure_ascii=False)
            except:
                last_result = str(last_result)

        return {
            "interpreter": cfg.get("interpreter", "bash").lower(),
            "script_body": cfg.get("script_body", ""),
            "input_mode": cfg.get("input_mode", "stdin").lower(),
            "return_type": cfg.get("return_type", "stdout").lower(),
            "input_val": last_result,
        }

    def exec(self, prep_res):
        interpreter = prep_res["interpreter"]
        script_body = prep_res["script_body"]
        input_mode = prep_res["input_mode"]
        return_type = prep_res["return_type"]
        input_val = prep_res["input_val"]

        if not script_body.strip():
            return "Error: No script content provided"

        # Prepare execution environment
        env = os.environ.copy()
        if input_mode == "env":
            env["POCKETFLOW_INPUT"] = input_val

        # Create a temporary file for the script to avoid shell escaping issues
        suffix = ".sh" if interpreter == "bash" else ".py"
        with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False) as tf:
            tf.write(script_body)
            temp_script_path = tf.name

        try:
            # Set up command
            if interpreter == "python":
                cmd = ["python3", temp_script_path]
            else:
                cmd = ["bash", temp_script_path]

            # Execute
            stdin_val = input_val if input_mode == "stdin" else None

            process = subprocess.run(
                cmd,
                input=stdin_val,
                capture_output=True,
                text=True,
                env=env,
                timeout=30,  # Safety timeout
            )

            result_data = {
                "stdout": process.stdout.strip(),
                "stderr": process.stderr.strip(),
                "exit_code": process.returncode,
                "success": process.returncode == 0,
            }

            # Handle return types
            if return_type == "exit_code":
                return process.returncode
            elif return_type == "json":
                return result_data
            else:  # default stdout
                if not result_data["success"] and not result_data["stdout"]:
                    return (
                        f"Error (Code {process.returncode}): {process.stderr.strip()}"
                    )
                return result_data["stdout"]

        except subprocess.TimeoutExpired:
            return "Error: Script execution timed out (30s limit)"
        except Exception as e:
            return f"Error executing script: {str(e)}"
        finally:
            if os.path.exists(temp_script_path):
                os.remove(temp_script_path)

    def post(self, shared, prep_res, exec_res):
        super().post(shared, prep_res, exec_res)
        return None
