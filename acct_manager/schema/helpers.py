from typing import Any
from pydantic.main import ModelMetaclass
from pydantic.schema import schema

# pylint: disable=import-error
from acct_manager import models


def find_exposed_models() -> list[Any]:
    """Find all models with _expose == True"""
    selected = []
    for modelname in dir(models):
        model = getattr(models, modelname)
        if isinstance(model, ModelMetaclass) and getattr(model, "_expose", False):
            selected.append(model)

    return selected


def generate_schema() -> dict[str, Any]:
    """Return schema dictionary for API models"""

    selected = find_exposed_models()
    return schema(selected, title="Onboarding Microservice API")
