from enum import Enum
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Union,
)

from pydantic import (
    BaseModel,
    Field,
)
from typing_extensions import (
    Annotated,
    Literal,
)

LABEL_DESCRIPTION = "The unique label of the step being referenced."
INPUT_NAME_DESCRIPTION = "The input name as defined by the workflow module corresponding to the step being referenced. For Galaxy tool steps these inputs should be normalized using '|' (e.g. 'cond|repeat_0|input')."
input_name_field = Field(description=INPUT_NAME_DESCRIPTION)
output_name_field = Field(
    description="The output name as defined by the workflow module corresponding to the step being referenced. The default is 'output', corresponding to the output defined by input step types.",
    default="output",
)
step_target_field = Field(description="The target step for this action.")


class StepReferenceByOrderIndex(BaseModel):
    order_index: int = Field(
        description="The order_index of the step being referenced. The order indices of a workflow start at 0."
    )


class StepReferenceByLabel(BaseModel):
    label: str = Field(description=LABEL_DESCRIPTION)


step_reference_union = Union[StepReferenceByOrderIndex, StepReferenceByLabel]


class InputReferenceByOrderIndex(StepReferenceByOrderIndex):
    input_name: str = input_name_field


class InputReferenceByLabel(StepReferenceByLabel):
    input_name: str = input_name_field


input_reference_union = Union[InputReferenceByOrderIndex, InputReferenceByLabel]


class OutputReferenceByOrderIndex(StepReferenceByOrderIndex):
    output_name: Optional[str] = output_name_field


class OutputReferenceByLabel(StepReferenceByLabel):
    output_name: Optional[str] = output_name_field


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


class Action(BaseAction):
    action_type: str

    @classmethod
    def __get_validators__(cls):
        yield cls.return_action

    @classmethod
    def return_action(cls, values):
        try:
            action_type = values["action_type"]
        except KeyError:
            raise ValueError(f"Missing required 'action_type' field for refactoring action: {values}")
        try:
            return ACTION_CLASSES_BY_TYPE[action_type](**values)
        except KeyError:
            raise ValueError(f"Unknown action_type encountered: {action_type}")


class UpdateStepLabelAction(BaseAction):
    action_type: Literal["update_step_label"]
    label: str = Field(description=LABEL_DESCRIPTION)
    step: step_reference_union = step_target_field


class UpdateStepPositionAction(BaseAction):
    action_type: Literal["update_step_position"]
    step: step_reference_union = step_target_field
    position_shift: Position


class AddStepAction(BaseAction):
    """Add a new action to the workflow.

    After the workflow is updated, an order_index will be assigned
    and this step may cause other steps to have their output_index
    adjusted.
    """

    action_type: Literal["add_step"]
    type: str = Field(description="Module type of the step to add, see galaxy.workflow.modules for available types.")
    tool_state: Optional[Dict[str, Any]] = None
    label: Optional[str] = Field(
        None,
        description="A unique label for the step being added, must be distinct from the labels already present in the workflow.",
    )
    position: Optional[Position] = Field(None, description="The location of the step in the Galaxy workflow editor.")


class ConnectAction(BaseAction):
    action_type: Literal["connect"]
    input: input_reference_union
    output: output_reference_union


class DisconnectAction(BaseAction):
    action_type: Literal["disconnect"]
    input: input_reference_union
    output: output_reference_union


class AddInputAction(BaseAction):
    action_type: Literal["add_input"]
    type: str
    label: Optional[str] = None
    position: Optional[Position] = None
    collection_type: Optional[str] = None
    restrictions: Optional[List[str]] = None
    restrict_on_connections: Optional[bool] = None
    suggestions: Optional[List[str]] = None
    optional: Optional[bool] = False
    default: Optional[Any] = None  # this probably needs to be revisited when we have more complex field types


class ExtractInputAction(BaseAction):
    action_type: Literal["extract_input"]
    input: input_reference_union
    label: Optional[str] = None
    position: Optional[Position] = None


class ExtractUntypedParameter(BaseAction):
    action_type: Literal["extract_untyped_parameter"]
    name: str
    label: Optional[str] = None  # defaults to name if unset
    position: Optional[Position] = None


class RemoveUnlabeledWorkflowOutputs(BaseAction):
    action_type: Literal["remove_unlabeled_workflow_outputs"]


class UpdateNameAction(BaseAction):
    action_type: Literal["update_name"]
    name: str


class UpdateAnnotationAction(BaseAction):
    action_type: Literal["update_annotation"]
    annotation: str


class UpdateLicenseAction(BaseAction):
    action_type: Literal["update_license"]
    license: str


class UpdateCreatorAction(BaseAction):
    action_type: Literal["update_creator"]
    creator: Any = None


class Report(BaseModel):
    markdown: str


class UpdateReportAction(BaseAction):
    action_type: Literal["update_report"]
    report: Report


class UpdateOutputLabelAction(BaseAction):
    action_type: Literal["update_output_label"]
    output: output_reference_union  # TODO: allow reference by output_label
    output_label: str


class FillStepDefaultsAction(BaseAction):
    action_type: Literal["fill_step_defaults"]
    step: step_reference_union


class FileDefaultsAction(BaseAction):
    action_type: Literal["fill_defaults"]


class UpgradeSubworkflowAction(BaseAction):
    action_type: Literal["upgrade_subworkflow"]
    step: step_reference_union = step_target_field
    # Once we start storing these actions in the database, this needs to be decoded
    # before adding it into the database.
    content_id: Optional[str] = None


class UpgradeToolAction(BaseAction):
    action_type: Literal["upgrade_tool"]
    step: step_reference_union = step_target_field
    tool_version: Optional[str] = None


class UpgradeAllStepsAction(BaseAction):
    action_type: Literal["upgrade_all_steps"]


union_action_classes = Union[
    AddInputAction,
    AddStepAction,
    ConnectAction,
    DisconnectAction,
    ExtractInputAction,
    ExtractUntypedParameter,
    FileDefaultsAction,
    FillStepDefaultsAction,
    UpdateAnnotationAction,
    UpdateCreatorAction,
    UpdateNameAction,
    UpdateLicenseAction,
    UpdateOutputLabelAction,
    UpdateReportAction,
    UpdateStepLabelAction,
    UpdateStepPositionAction,
    UpgradeSubworkflowAction,
    UpgradeToolAction,
    UpgradeAllStepsAction,
    RemoveUnlabeledWorkflowOutputs,
]


ACTION_CLASSES_BY_TYPE = {}
for action_class in union_action_classes.__args__:  # type: ignore[attr-defined]
    action_type_def = action_class.model_json_schema()["properties"]["action_type"]
    try:
        # pydantic 1.8
        action_type = action_type_def["enum"][0]
    except KeyError:
        # pydantic 1.7
        action_type = action_type_def["const"]

    ACTION_CLASSES_BY_TYPE[action_type] = action_class


class RefactorActions(BaseModel):
    actions: List[Annotated[union_action_classes, Field(discriminator="action_type")]]
    dry_run: bool = False


class RefactorActionExecutionMessageTypeEnum(str, Enum):
    tool_version_change = "tool_version_change"
    tool_state_adjustment = "tool_state_adjustment"
    connection_drop_forced = "connection_drop_forced"
    workflow_output_drop_forced = "workflow_output_drop_forced"


INPUT_REFERENCE = """

Messages don't have to be bound to a step, but if they are they will
have a step_label and order_index included in the execution message.
These are the label and order_index before applying the refactoring,
the result of applying the action may change one or both of these.
If connections are dropped this step reference will refer to the
step with the previously connected input.
"""


class RefactorActionExecutionMessage(BaseModel):
    message: str
    message_type: RefactorActionExecutionMessageTypeEnum
    step_label: Optional[str] = Field(
        None, description=f"Reference to the step the message refers to. ${INPUT_REFERENCE}"
    )
    order_index: Optional[int] = Field(
        None, description=f"Reference to the step the message refers to. ${INPUT_REFERENCE}"
    )
    input_name: Optional[str] = Field(
        None,
        description=f"""If this message is about an input to a step,
this field describes the target input name. ${INPUT_NAME_DESCRIPTION}""",
    )
    output_name: Optional[str] = Field(
        None,
        description="""If this message is about an output to a step,
this field describes the target output name. The output name as defined by the workflow module corresponding to the step being referenced.
""",
    )
    from_step_label: Optional[str] = Field(
        None,
        description="""For dropped connections these optional attributes refer to the output
side of the connection that was dropped.""",
    )
    from_order_index: Optional[int] = Field(
        None,
        description="""For dropped connections these optional attributes refer to the output
side of the connection that was dropped.""",
    )
    output_label: Optional[str] = Field(
        None, description="If the message_type is workflow_output_drop_forced, this is the output label dropped."
    )


class RefactorActionExecution(BaseModel):
    action: union_action_classes
    messages: List[RefactorActionExecutionMessage]
