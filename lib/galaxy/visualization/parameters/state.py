"""Single-state wrapper around a visualization embed config.

Tools carry a dozen state representations (request, internal, job, test case,
workflow step, ...); a visualization embed config has exactly one, so this is a
thin analog of ``galaxy.tool_util.parameters.state.ToolState``.
"""

from typing import (
    Any,
    Optional,
)

from .models import (
    create_request_model,
    VISUALIZATION_REQUEST_MODEL_NAME,
    VisualizationParameterBundleModel,
)
from .validation import validate_against_model


class VisualizationState:
    def __init__(self, input_state: dict[str, Any]):
        self.input_state = input_state

    def validate(self, bundle: VisualizationParameterBundleModel, name: Optional[str] = None) -> None:
        model = create_request_model(bundle, name or VISUALIZATION_REQUEST_MODEL_NAME)
        validate_against_model(model, self.input_state)


# The single representation is the authored request; the alias mirrors tool naming.
RequestVisualizationState = VisualizationState
