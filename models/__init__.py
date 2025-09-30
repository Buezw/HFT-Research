# models/__init__.py
import importlib.util
import pathlib

package_path = pathlib.Path(__file__).parent

for py_file in package_path.rglob("*.py"):
    if py_file.name == "__init__.py":
        continue
    rel_path = py_file.relative_to(package_path.parent)
    module_name = ".".join(rel_path.with_suffix("").parts)
    importlib.import_module(module_name)