"""Generate jsonschema descriptions of API objects"""

from typing import Any
from pydantic.main import ModelMetaclass
from pydantic.schema import schema
import yaml

# pylint: disable=import-error
from acct_manager import models


def generate_schema() -> dict[str, Any]:
    """Return schema dictionary for API models"""

    selected = []
    for modelname in dir(models):
        model = getattr(models, modelname)
        if isinstance(model, ModelMetaclass) and getattr(model, "_expose", False):
            selected.append(model)

    return schema(selected, title="Onboarding Microservice API")


if __name__ == "__main__":
    defs = generate_schema()
    print(yaml.safe_dump(defs))
