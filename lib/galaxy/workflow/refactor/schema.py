from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel
from typing_extensions import Literal


class StepReferenceByOrderIndex(BaseModel):
    order_index: int


class StepReferenceByLabel(BaseModel):
    label: str


step_reference_union = Union[StepReferenceByOrderIndex, StepReferenceByLabel]


class InputReferenceByOrderIndex(StepReferenceByOrderIndex):
    input_name: str


class InputReferenceByLabel(StepReferenceByLabel):
    input_name: str


input_reference_union = Union[InputReferenceByOrderIndex, InputReferenceByLabel]


class OutputReferenceByOrderIndex(StepReferenceByOrderIndex):
    output_name: Optional[str] = "output"


class OutputReferenceByLabel(StepReferenceByLabel):
    output_name: Optional[str] = "output"


output_reference_union = Union[OutputReferenceByOrderIndex, OutputReferenceByLabel]


class Position(BaseModel):
    left: float
    top: float

    def to_dict(self):
        position = {
            "left": self.left,
            "top": self.top,
        }
        return position


class BaseAction(BaseModel):
    """Refactoring actions."""


class Action:
    action_type: str

    @classmethod
    def __get_validators__(cls):
        yield cls.return_action

    @classmethod
    def return_action(cls, values):
        try:
            action_type = values["action_type"]
        except KeyError:
            raise ValueError(
                f"Missing required 'action_type' field for refactoring action: {values}"
            )
        try:
            return ACTION_CLASSES_BY_TYPE[action_type](**values)
        except KeyError:
            raise ValueError(f"Unknown action_type encountered: {action_type}")


class UpdateStepLabelAction(BaseAction):
    action_type: Literal['update_step_label']
    label: str
    step: step_reference_union


class UpdateStepPositionAction(BaseAction):
    action_type: Literal['update_step_position']
    step: step_reference_union
    position: Position


class AddStepAction(BaseAction):
    action_type: Literal['add_step']
    type: str  # module.type
    tool_state: Optional[Dict[str, Any]]
    label: Optional[str]
    position: Optional[Position]


class ConnectAction(BaseAction):
    action_type: Literal['connect']
    input: input_reference_union
    output: output_reference_union


class DisconnectAction(BaseAction):
    action_type: Literal['disconnect']
    input: input_reference_union
    output: output_reference_union


class AddInputAction(BaseAction):
    action_type: Literal['add_input']
    type: str
    label: Optional[str]
    position: Optional[Position]
    collection_type: Optional[str]
    restrictions: Optional[List[str]]
    restrict_on_connections: Optional[bool]
    suggestions: Optional[List[str]]
    optional: Optional[bool] = False
    default: Optional[Any]  # this probably needs to be revisited when we have more complex field types


class ExtractInputAction(BaseAction):
    action_type: Literal['extract_input']
    input: input_reference_union
    label: Optional[str]
    position: Optional[Position]


class ExtractLegacyParameter(BaseAction):
    action_type: Literal['extract_legacy_parameter']
    name: str
    label: Optional[str]  # defaults to name if unset
    position: Optional[Position]


class RemoveUnlabeledWorkflowOutputs(BaseAction):
    action_type: Literal['remove_unlabeled_workflow_outputs']


class UpdateNameAction(BaseAction):
    action_type: Literal['update_name']
    name: str


class UpdateAnnotationAction(BaseAction):
    action_type: Literal['update_annotation']
    annotation: str


class UpdateLicenseAction(BaseAction):
    action_type: Literal['update_license']
    license: str


class UpdateCreatorAction(BaseAction):
    action_type: Literal['update_creator']
    creator: Any


class Report(BaseModel):
    markdown: str


class UpdateReportAction(BaseAction):
    action_type: Literal['update_report']
    report: Report


class FillStepDefaultsAction(BaseAction):
    action_type: Literal['fill_step_defaults']
    step: step_reference_union


union_action_classes = Union[
    AddInputAction,
    AddStepAction,
    ConnectAction,
    DisconnectAction,
    ExtractInputAction,
    ExtractLegacyParameter,
    FillStepDefaultsAction,
    UpdateAnnotationAction,
    UpdateCreatorAction,
    UpdateNameAction,
    UpdateLicenseAction,
    UpdateReportAction,
    UpdateStepLabelAction,
    UpdateStepPositionAction,
    RemoveUnlabeledWorkflowOutputs,
]


ACTION_CLASSES_BY_TYPE = {}
for action_class in union_action_classes.__args__:  # type: ignore
    action_type = action_class.schema()["properties"]["action_type"]["const"]
    ACTION_CLASSES_BY_TYPE[action_type] = action_class


class RefactorRequest(BaseModel):
    actions: List[Action]
    dry_run: bool = False
