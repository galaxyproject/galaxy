from enum import Enum
from typing import (
    Annotated,
    Any,
    Literal,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
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


step_reference_union = StepReferenceByOrderIndex | StepReferenceByLabel


class InputReferenceByOrderIndex(StepReferenceByOrderIndex):
    input_name: str = input_name_field


class InputReferenceByLabel(StepReferenceByLabel):
    input_name: str = input_name_field


input_reference_union = InputReferenceByOrderIndex | InputReferenceByLabel


class OutputReferenceByOrderIndex(StepReferenceByOrderIndex):
    output_name: str | None = output_name_field


class OutputReferenceByLabel(StepReferenceByLabel):
    output_name: str | None = output_name_field


output_reference_union = OutputReferenceByOrderIndex | OutputReferenceByLabel


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
    tool_state: dict[str, Any] | None = None
    label: str | None = Field(
        None,
        description="A unique label for the step being added, must be distinct from the labels already present in the workflow.",
    )
    position: Position | None = Field(None, description="The location of the step in the Galaxy workflow editor.")


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
    label: str | None = None
    position: Position | None = None
    collection_type: str | None = None
    restrictions: list[str] | None = None
    restrict_on_connections: bool | None = None
    suggestions: list[str] | None = None
    optional: bool | None = False
    default: Any | None = None  # this probably needs to be revisited when we have more complex field types


class ExtractInputAction(BaseAction):
    action_type: Literal["extract_input"]
    input: input_reference_union
    label: str | None = None
    position: Position | None = None


class ExtractUntypedParameter(BaseAction):
    action_type: Literal["extract_untyped_parameter"]
    name: str
    label: str | None = None  # defaults to name if unset
    position: Position | None = None


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
    """Switch a sub-workflow step to another version of its sub-workflow, or to another workflow.

    Without a target, a sub-workflow imported from a TRS server moves to the newest numbered TRS
    version if that is newer than the current one, and any other sub-workflow moves to the newest
    version of its stored workflow.

    A target owned by someone else, e.g. a published workflow, is copied into this user's account as
    a hidden workflow, and the step uses the copy. A dry run reads the target without copying it.
    """

    # An unrecognized target would otherwise fall through to the upgrade without a target.
    model_config = ConfigDict(extra="forbid")

    action_type: Literal["upgrade_subworkflow"]
    step: step_reference_union = step_target_field
    # Once we start storing these actions in the database, this needs to be decoded
    # before adding it into the database.
    content_id: str | None = Field(
        default=None,
        description="The encoded id of the workflow version (not stored workflow) to switch to. "
        "It may be a version of another workflow this user owns or can access.",
    )
    stored_workflow_id: str | None = Field(
        default=None,
        description="The encoded id of another stored workflow this user owns or can access, e.g. a published one, "
        "to switch to. Uses its newest version, or the one given by `version`.",
    )
    version: int | None = Field(
        default=None,
        ge=0,
        description="The version to switch to, counted from 0 for the oldest, as listed by "
        "`/api/workflows/{workflow_id}/versions`. A version of `stored_workflow_id` if given, "
        "else of the sub-workflow's own stored workflow.",
    )
    trs_version_id: str | None = Field(
        default=None,
        description="The TRS version to switch a sub-workflow imported from a TRS server to. "
        "The version is imported if this user has no copy of it yet, also during a dry run.",
    )
    recursive: bool = Field(
        default=False,
        description="Also upgrade the sub-workflow steps nested inside the target sub-workflow to their newest "
        "versions, innermost first, saving a new version of each nested sub-workflow that changes. Sub-workflows "
        "imported from a URL or a TRS server are left as published, and so are a target copied from another user and "
        "a target that is not the newest version of its stored workflow. A dry run saves no nested upgrades: it "
        "reports what they would change, but the returned workflow still points at the target's current nested "
        "versions.",
    )

    @model_validator(mode="after")
    def at_most_one_target(self) -> "UpgradeSubworkflowAction":
        version = None if self.stored_workflow_id is not None else self.version
        targets = [t for t in (self.content_id, self.stored_workflow_id, version, self.trs_version_id) if t is not None]
        if len(targets) > 1:
            raise ValueError(
                "Specify at most one of content_id, stored_workflow_id (optionally with version), "
                "version and trs_version_id."
            )
        return self


class UpgradeToolAction(BaseAction):
    action_type: Literal["upgrade_tool"]
    step: step_reference_union = step_target_field
    tool_version: str | None = None


class UpgradeAllStepsAction(BaseAction):
    action_type: Literal["upgrade_all_steps"]


union_action_classes = (
    AddInputAction
    | AddStepAction
    | ConnectAction
    | DisconnectAction
    | ExtractInputAction
    | ExtractUntypedParameter
    | FileDefaultsAction
    | FillStepDefaultsAction
    | UpdateAnnotationAction
    | UpdateCreatorAction
    | UpdateNameAction
    | UpdateLicenseAction
    | UpdateOutputLabelAction
    | UpdateReportAction
    | UpdateStepLabelAction
    | UpdateStepPositionAction
    | UpgradeSubworkflowAction
    | UpgradeToolAction
    | UpgradeAllStepsAction
    | RemoveUnlabeledWorkflowOutputs
)


ACTION_CLASSES_BY_TYPE = {}
for action_class in union_action_classes.__args__:
    action_type_def = action_class.model_json_schema()["properties"]["action_type"]
    try:
        # pydantic 1.8
        action_type = action_type_def["enum"][0]
    except KeyError:
        # pydantic 1.7
        action_type = action_type_def["const"]

    ACTION_CLASSES_BY_TYPE[action_type] = action_class


class RefactorActions(BaseModel):
    actions: list[Annotated[union_action_classes, Field(discriminator="action_type")]]
    dry_run: bool = False


class RefactorActionExecutionMessageTypeEnum(str, Enum):
    tool_version_change = "tool_version_change"
    tool_state_adjustment = "tool_state_adjustment"
    connection_drop_forced = "connection_drop_forced"
    workflow_output_drop_forced = "workflow_output_drop_forced"
    subworkflow_versions_unavailable = "subworkflow_versions_unavailable"


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
    step_label: str | None = Field(None, description=f"Reference to the step the message refers to. ${INPUT_REFERENCE}")
    order_index: int | None = Field(
        None, description=f"Reference to the step the message refers to. ${INPUT_REFERENCE}"
    )
    input_name: str | None = Field(
        None,
        description=f"""If this message is about an input to a step,
this field describes the target input name. ${INPUT_NAME_DESCRIPTION}""",
    )
    output_name: str | None = Field(
        None,
        description="""If this message is about an output to a step,
this field describes the target output name. The output name as defined by the workflow module corresponding to the step being referenced.
""",
    )
    from_step_label: str | None = Field(
        None,
        description="""For dropped connections these optional attributes refer to the output
side of the connection that was dropped.""",
    )
    from_order_index: int | None = Field(
        None,
        description="""For dropped connections these optional attributes refer to the output
side of the connection that was dropped.""",
    )
    output_label: str | None = Field(
        None, description="If the message_type is workflow_output_drop_forced, this is the output label dropped."
    )


class RefactorActionExecution(BaseModel):
    action: union_action_classes
    messages: list[RefactorActionExecutionMessage]
