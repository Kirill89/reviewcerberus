from typing import Any

from .providers import create_model

# Single global model instance created via factory
model: Any = create_model()
