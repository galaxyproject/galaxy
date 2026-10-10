import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
CONVERTERS = ROOT / "lib/galaxy/datatypes/converters"

pytest.importorskip("pyarrow")


def load_converter(name):
    spec = importlib.util.spec_from_file_location(name, CONVERTERS / f"{name}.py")
    assert spec is not None, "spec is None"
    assert spec.loader is not None, "spec.loader is None"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


to_parquet = load_converter("tabular_to_parquet_converter")
to_tsv = load_converter("parquet_to_tabular_converter")


def converter_script(name):
    return CONVERTERS / f"{name}.py"


def run_converter(name, source, destination, *args):
    subprocess.run([sys.executable, str(converter_script(name)), str(source), str(destination), *args], check=True)
