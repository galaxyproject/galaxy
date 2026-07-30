"""Typed parameter models and validation for visualization plugins.

A deliberately smaller parallel to ``galaxy.tool_util.parameters``: a flat set of
``settings`` inputs plus a single top-level ``tracks`` repeat, one state
representation, and no coupling to the tool request/job/workflow lifecycle.
"""

from .factory import (
    input_models_for_visualization,
    input_models_for_visualization_path,
    VisualizationParameterParsingException,
)
from .models import (
    BooleanParameterModel,
    ColorParameterModel,
    ConditionalParameterModel,
    create_request_model,
    DataColumnParameterModel,
    DataJsonParameterModel,
    DataParameterModel,
    DataTableParameterModel,
    FloatParameterModel,
    IntegerParameterModel,
    LabelValue,
    SelectParameterModel,
    TextParameterModel,
    VisualizationParameterBundleModel,
    VisualizationParameterT,
    VisualizationWhen,
)
from .state import (
    RequestVisualizationState,
    VisualizationState,
)
from .validation import validate_against_model

__all__ = (
    "BooleanParameterModel",
    "ColorParameterModel",
    "ConditionalParameterModel",
    "create_request_model",
    "DataColumnParameterModel",
    "DataJsonParameterModel",
    "DataParameterModel",
    "DataTableParameterModel",
    "FloatParameterModel",
    "input_models_for_visualization",
    "input_models_for_visualization_path",
    "IntegerParameterModel",
    "LabelValue",
    "RequestVisualizationState",
    "SelectParameterModel",
    "TextParameterModel",
    "validate_against_model",
    "VisualizationParameterBundleModel",
    "VisualizationParameterParsingException",
    "VisualizationParameterT",
    "VisualizationState",
    "VisualizationWhen",
)
