"""Generate jsonschema descriptions of API objects"""

import yaml

# pylint: disable=import-error
from acct_manager.schema import helpers


def main() -> None:
    """Print YAML version of schema"""
    defs = helpers.generate_schema()
    print(yaml.safe_dump(defs))


if __name__ == "__main__":
    main()
