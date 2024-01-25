from abc import (
    ABC,
    abstractmethod,
)
from typing import (
    Any,
    Dict,
    Optional,
    Type,
)

from pydantic import BaseModel
from typing_extensions import Literal

from .models import (
    create_request_internal_model,
    create_request_model,
    StateRepresentationT,
    ToolParameterBundle,
    validate_against_model,
)


class ToolState(ABC):
    input_state: Dict[str, Any]

    def __init__(self, input_state: Dict[str, Any]):
        self.input_state = input_state

    def _validate(self, pydantic_model: Type[BaseModel]) -> None:
        validate_against_model(pydantic_model, self.input_state)

    def validate(self, input_models: ToolParameterBundle) -> None:
        base_model = self._to_base_model(input_models)
        if base_model is None:
            raise NotImplementedError(
                f"Validating tool state against state representation {self.state_representation} is not implemented."
            )
        self._validate(base_model)

    @property
    @abstractmethod
    def state_representation(self) -> StateRepresentationT:
        """Get state representation of the inputs."""

    def _to_base_model(self, input_models: ToolParameterBundle) -> Optional[Type[BaseModel]]:
        return None


class RequestToolState(ToolState):
    state_representation: Literal["request"] = "request"

    def _to_base_model(self, input_models: ToolParameterBundle) -> Type[BaseModel]:
        return create_request_model(input_models)


class RequestInternalToolState(ToolState):
    state_representation: Literal["request_internal"] = "request_internal"

    def _to_base_model(self, input_models: ToolParameterBundle) -> Type[BaseModel]:
        return create_request_internal_model(input_models)


class JobInternalToolState(ToolState):
    state_representation: Literal["job_internal"] = "job_internal"

    def _to_base_model(self, input_models: ToolParameterBundle) -> Type[BaseModel]:
        # implement a job model...
        return create_request_internal_model(input_models)


class TestCaseToolState(ToolState):
    state_representation: Literal["test_case"] = "test_case"

    def _to_base_model(self, input_models: ToolParameterBundle) -> Type[BaseModel]:
        # implement a test case model...
        return create_request_internal_model(input_models)
