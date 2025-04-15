from galaxy.tool_util_models import Tests

simple_json_test = """
[{ "doc": "Test simple use of __ZIP_COLLECTION__ in a workflow.",
   "job": {
        "test_input_1": "samp1 10.0  samp2 20.0  ",
        "test_input_2": "samp1 20.0  samp2 40.0  "
    },
    "outputs": {
        "out": {
            "asserts": [
                {"that": "has_text",
                 "text": "samp1 10.0  samp2 20.0  samp1 20.0  samp2 40.0"
                }
            ]
        }
    }
}]
"""


def test_simple_validate():
    Tests.model_validate_json(simple_json_test)
