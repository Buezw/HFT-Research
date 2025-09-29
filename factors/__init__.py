# factors/__init__.py
# Auto import all .py files in factors/ and its subdirectories (recursively)

import importlib.util
import pathlib

package_path = pathlib.Path(__file__).parent

# Recursively scan all .py files (exclude __init__.py and base/engine)
for py_file in package_path.rglob("*.py"):
    if py_file.name == "__init__.py":
        continue

    # Build module name like "factors.price.momentum"
    rel_path = py_file.relative_to(package_path.parent)
    module_name = ".".join(rel_path.with_suffix("").parts)

    importlib.import_module(module_name)
