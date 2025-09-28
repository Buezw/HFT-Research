# factors/base.py
FACTOR_REGISTRY = {}

def register_factor(name=None, category=None, desc=None):
    """装饰器：注册因子到全局表"""
    def decorator(func):
        fname = name or func.__name__
        FACTOR_REGISTRY[fname] = {
            "func": func,
            "category": category,
            "desc": desc,
        }
        return func
    return decorator
