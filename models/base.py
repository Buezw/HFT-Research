# models/base.py
# Model registry for HFTSim
MODEL_REGISTRY = {}

def register_model(name: str, desc: str, task: str = "classification"):
    """
    Decorator to register a model class.
    - name: short name of the model
    - desc: description of the model
    - task: type of task ("classification" or "regression")
    """
    def decorator(cls):
        MODEL_REGISTRY[name] = {
            "name": name,
            "desc": desc,
            "task": task,
            "class": cls
        }
        return cls
    return decorator


def get_all_models():
    """Return all registered models (with class objects)"""
    return MODEL_REGISTRY
