from galaxy.util.pyodide import infer_requirements_from_python


def test_infer_requirements_from_imports_maps_common_packages():
    code = "\n".join(
        [
            "import os",
            "import numpy as np",
            "from sklearn.model_selection import train_test_split",
            "from PIL import Image",
            "import yaml",
        ]
    )
    requirements = infer_requirements_from_python(code)
    # stdlib is ignored; imports are mapped where needed.
    assert "os" not in requirements
    assert "numpy" in requirements
    assert "scikit-learn" in requirements
    assert "pillow" in requirements
    assert "pyyaml" in requirements


def test_infer_requirements_respects_explicit_marker():
    code = "\n".join(
        [
            "# requirements: pandas, matplotlib",
            "import json",
            "import numpy as np",
        ]
    )
    requirements = infer_requirements_from_python(code)
    assert "pandas" in requirements
    assert "matplotlib" in requirements
    # We still union in inferred imports.
    assert "numpy" in requirements
    assert "json" not in requirements
