import json
import argparse

from pydantic import TypeAdapter

from galaxy.tool_util_models import Tests


def write_test_schema(schema_path: str):
    with open(schema_path, "w") as f:
        f.write(json.dumps(TypeAdapter(Tests).json_schema()))


def main():
    parser = argparse.ArgumentParser(description="Write test schema to file.")
    parser.add_argument("schema_path", help="Path to write the schema file to.")
    args = parser.parse_args()
    write_test_schema(args.schema_path)


if __name__ == "__main__":
    main()
