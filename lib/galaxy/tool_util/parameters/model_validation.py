from typing import (
    Any,
    Dict,
    Optional,
    Type,
)

from pydantic import (
    BaseModel,
    ValidationError,
)
from typing_extensions import (
    Protocol,
)

from galaxy.exceptions import RequestParameterInvalidException
from galaxy.tool_util_models.parameters import (
    create_field_model,
    DEFAULT_MODEL_NAME,
    RawStateDict,
    StateRepresentationT,
    ToolParameterBundle,
)


def validate_against_model(pydantic_model: Type[BaseModel], parameter_state: Dict[str, Any]) -> None:
    try:
        pydantic_model(**parameter_state)
    except ValidationError as e:
        # TODO: Improve this or maybe add a handler for this in the FastAPI exception
        # handler.
        raise RequestParameterInvalidException(str(e))


class ValidationFunctionT(Protocol):

    def __call__(self, tool: ToolParameterBundle, request: RawStateDict, name: Optional[str] = None) -> None: ...


def validate_model_type_factory(state_representation: StateRepresentationT) -> ValidationFunctionT:

    def validate_request(tool: ToolParameterBundle, request: Dict[str, Any], name: Optional[str] = None) -> None:
        name = name or DEFAULT_MODEL_NAME
        pydantic_model = create_field_model(tool.parameters, name=name, state_representation=state_representation)
        validate_against_model(pydantic_model, request)

    return validate_request


validate_request = validate_model_type_factory("request")
validate_internal_request = validate_model_type_factory("request_internal")
validate_internal_request_dereferenced = validate_model_type_factory("request_internal_dereferenced")
validate_landing_request = validate_model_type_factory("landing_request")
validate_internal_landing_request = validate_model_type_factory("landing_request_internal")
validate_internal_job = validate_model_type_factory("job_internal")
validate_test_case = validate_model_type_factory("test_case_xml")
validate_workflow_step = validate_model_type_factory("workflow_step")
validate_workflow_step_linked = validate_model_type_factory("workflow_step_linked")
