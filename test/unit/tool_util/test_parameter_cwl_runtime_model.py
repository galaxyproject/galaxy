from galaxy.tool_util.parameters.convert import cwl_runtime_model
from galaxy.tool_util.unittest_utils.parameters import parameter_bundle_for_file


def test_cwl_runtime_model_conditional():
    model = parameter_bundle_for_file("gx_conditional_select")
    rval = cwl_runtime_model(model)
    assert rval


def test_cwl_runtime_model_data():
    model = parameter_bundle_for_file("gx_data")
    rval = cwl_runtime_model(model)
    assert rval


def test_cwl_runtime_model_data_collection_list():
    model = parameter_bundle_for_file("gx_data_collection_list")
    rval = cwl_runtime_model(model)
    assert rval


def test_cwl_runtime_model_data_collection_unknown_type():
    model = parameter_bundle_for_file("gx_data_collection")
    rval = cwl_runtime_model(model)
    assert rval
