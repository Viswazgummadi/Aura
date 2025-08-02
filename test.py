# File: find_my_class.py
import pkgutil
import importlib
import inspect
import langgraph

CLASS_TO_FIND = "ToolExecutor"

print(f"--- Searching for '{CLASS_TO_FIND}' in the 'langgraph' library ---")

found_path = None

# Walk through all modules and submodules in the langgraph package
for importer, modname, ispkg in pkgutil.walk_packages(path=langgraph.__path__,
                                                      prefix=langgraph.__name__ + '.',
                                                      onerror=lambda x: None):
    try:
        # Try to import the module
        module = importlib.import_module(modname)
        
        # Inspect the members of the module
        for name, obj in inspect.getmembers(module):
            if name == CLASS_TO_FIND and inspect.isclass(obj):
                found_path = modname
                break
    except ImportError:
        # Some submodules might not be importable, which is fine
        continue
    if found_path:
        break

print("\n--- Search Complete ---")

if found_path:
    print(f"✅ Found it! The correct import path is:")
    print(f"\nfrom {found_path} import {CLASS_TO_FIND}\n")
else:
    print(f"❌ Could not find the class '{CLASS_TO_FIND}' anywhere in the langgraph library.")
    print("   This might mean it's named something else or your library version is very old.")