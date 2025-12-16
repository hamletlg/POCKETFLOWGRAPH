import pocketflow
import inspect
import pkgutil

print("PocketFlow imported successfully")
print(f"Version: {pocketflow.__version__ if hasattr(pocketflow, '__version__') else 'Unknown'}")

def list_module_content(module, prefix=""):
    print(f"{prefix}Module: {module.__name__}")
    for name, obj in inspect.getmembers(module):
        if not name.startswith("__"):
            if inspect.isclass(obj):
                print(f"{prefix}  Class: {name}")
            elif inspect.isfunction(obj):
                print(f"{prefix}  Function: {name}")
            elif inspect.ismodule(obj):
                # print(f"{prefix}  Module: {name}") # Avoid deep recursion for now
                pass

list_module_content(pocketflow)

# Start digging into submodules if possible
if hasattr(pocketflow, "__path__"):
    for importer, modname, ispkg in pkgutil.iter_modules(pocketflow.__path__):
        print(f"Submodule: {modname}")
