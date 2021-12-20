"""Generate jsonschema descriptions of API objects"""

import argparse
from typing import Any

import json
from pydantic.schema import schema
import yaml

# pylint: disable=import-error
from acct_manager import models


def generate_schema() -> dict[str, Any]:
    """Return schema dictionary for API models"""

    return schema(models.public_models, title="Onboarding Microservice API")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments"""

    p = argparse.ArgumentParser()
    p.add_argument(
        "--json",
        "-j",
        action="store_const",
        const="json",
        dest="output_format",
        help="Output openapi schema in JSON format",
    )
    p.add_argument(
        "--yaml",
        "-y",
        action="store_const",
        const="yaml",
        dest="output_format",
        help="Output openapi schema in YAML format",
    )
    p.set_defaults(output_format="yaml")

    return p.parse_args()


def main() -> None:
    """Print schema to stdout"""

    args = parse_args()
    defs = generate_schema()

    if args.output_format == "yaml":
        print(yaml.safe_dump(defs))
    elif args.output_format == "json":
        print(json.dumps(defs, indent=2))


if __name__ == "__main__":
    main()
