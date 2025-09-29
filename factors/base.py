# factors/base.py

FACTOR_REGISTRY = {}  # name -> {func, category, desc, formula, explanation}

def register_factor(name: str, category: str, desc: str, formula: str = None, explanation: str = None):
    """
    Decorator: register a factor with metadata
    """
    def decorator(func):
        FACTOR_REGISTRY[name] = {
            "func": func,
            "category": category,
            "desc": desc,
            "formula": formula,
            "explanation": explanation,
        }
        return func
    return decorator


def get_all_factors():
    """
    Return all registered factors' metadata
    """
    return {
        name: {
            "category": meta["category"],
            "desc": meta["desc"],
            "formula": meta.get("formula"),
            "explanation": meta.get("explanation"),
        }
        for name, meta in FACTOR_REGISTRY.items()
    }
