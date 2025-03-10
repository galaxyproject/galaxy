from abc import (
    ABC,
    abstractmethod,
)
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Type,
    Union,
)

from pydantic import BaseModel
from typing_extensions import Literal

from galaxy.tool_util_models.parameters import (
    create_job_internal_model,
    create_landing_request_internal_model,
    create_landing_request_model,
    create_request_internal_dereferenced_model,
    create_request_internal_model,
    create_request_model,
    create_test_case_model,
    create_workflow_step_linked_model,
    create_workflow_step_model,
    StateRepresentationT,
    ToolParameterBundle,
    ToolParameterBundleModel,
    ToolParameterT,
)
from .model_validation import (
    validate_against_model,
)

HasToolParameters = Union[List[ToolParameterT], ToolParameterBundle]


class ToolState(ABC):
    input_state: Dict[str, Any]

    def __init__(self, input_state: Dict[str, Any]):
        self.input_state = input_state

    def _validate(self, pydantic_model: Type[BaseModel]) -> None:
        validate_against_model(pydantic_model, self.input_state)

    def validate(self, parameters: HasToolParameters, name: Optional[str] = None) -> None:
        base_model = self.parameter_model_for(parameters, name=name)
        if base_model is None:
            raise NotImplementedError(
                f"Validating tool state against state representation {self.state_representation} is not implemented."
            )
        self._validate(base_model)

    @property
    @abstractmethod
    def state_representation(self) -> StateRepresentationT:
        """Get state representation of the inputs."""

    @classmethod
    def parameter_model_for(cls, parameters: HasToolParameters, name: Optional[str] = None) -> Type[BaseModel]:
        bundle: ToolParameterBundle
        if isinstance(parameters, list):
            bundle = ToolParameterBundleModel(parameters=parameters)
        else:
            bundle = parameters
        return cls._parameter_model_for(bundle, name=name)

    @classmethod
    @abstractmethod
    def _parameter_model_for(cls, parameters: ToolParameterBundle, name: Optional[str] = None) -> Type[BaseModel]:
        """Return a model type for this tool state kind."""


class RequestToolState(ToolState):
    state_representation: Literal["request"] = "request"

    @classmethod
    def _parameter_model_for(cls, parameters: ToolParameterBundle, name: Optional[str] = None) -> Type[BaseModel]:
        return create_request_model(parameters, name)


class RequestInternalToolState(ToolState):
    state_representation: Literal["request_internal"] = "request_internal"

    @classmethod
    def _parameter_model_for(cls, parameters: ToolParameterBundle, name: Optional[str] = None) -> Type[BaseModel]:
        return create_request_internal_model(parameters, name)


class LandingRequestToolState(ToolState):
    state_representation: Literal["landing_request"] = "landing_request"

    @classmethod
    def _parameter_model_for(cls, parameters: ToolParameterBundle, name: Optional[str] = None) -> Type[BaseModel]:
        return create_landing_request_model(parameters, name)


class LandingRequestInternalToolState(ToolState):
    state_representation: Literal["landing_request_internal"] = "landing_request_internal"

    @classmethod
    def _parameter_model_for(cls, parameters: ToolParameterBundle, name: Optional[str] = None) -> Type[BaseModel]:
        return create_landing_request_internal_model(parameters, name)


class RequestInternalDereferencedToolState(ToolState):
    state_representation: Literal["request_internal_dereferenced"] = "request_internal_dereferenced"

    @classmethod
    def _parameter_model_for(cls, parameters: ToolParameterBundle, name: Optional[str] = None) -> Type[BaseModel]:
        return create_request_internal_dereferenced_model(parameters, name)


class JobInternalToolState(ToolState):
    state_representation: Literal["job_internal"] = "job_internal"

    @classmethod
    def _parameter_model_for(cls, parameters: ToolParameterBundle, name: Optional[str] = None) -> Type[BaseModel]:
        return create_job_internal_model(parameters, name)


class TestCaseToolState(ToolState):
    state_representation: Literal["test_case_xml"] = "test_case_xml"

    @classmethod
    def _parameter_model_for(cls, parameters: ToolParameterBundle, name: Optional[str] = None) -> Type[BaseModel]:
        # implement a test case model...
        return create_test_case_model(parameters, name)


class WorkflowStepToolState(ToolState):
    state_representation: Literal["workflow_step"] = "workflow_step"

    @classmethod
    def _parameter_model_for(cls, parameters: ToolParameterBundle, name: Optional[str] = None) -> Type[BaseModel]:
        return create_workflow_step_model(parameters, name)


class WorkflowStepLinkedToolState(ToolState):
    state_representation: Literal["workflow_step_linked"] = "workflow_step_linked"

    @classmethod
    def _parameter_model_for(cls, parameters: ToolParameterBundle, name: Optional[str] = None) -> Type[BaseModel]:
        return create_workflow_step_linked_model(parameters, name)
