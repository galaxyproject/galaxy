import os
import sys

try:
    from pydantic2ts import generate_typescript_defs
except ImportError:
    generate_typescript_defs = None


sys.path.insert(1, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, "lib")))


def main():
    if generate_typescript_defs is None:
        raise Exception("Please install pydantic-to-typescript into Galaxy's environment")
    generate_typescript_defs("galaxy.tool_util.parser.parameters", "client/src/components/Tool/parameterModels.ts")


if __name__ == "__main__":
    main()
