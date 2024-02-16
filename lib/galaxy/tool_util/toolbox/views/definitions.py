from enum import Enum
from typing import (
    Any,
    cast,
    List,
    Optional,
    Union,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)
from typing_extensions import (
    Annotated,
    Literal,
)


class StaticToolBoxViewTypeEnum(str, Enum):
    generic = "generic"
    activity = "activity"
    publication = "publication"
    training = "training"


class ExcludeTool(BaseModel):
    tool_id: str


class ExcludeToolRegex(BaseModel):
    tool_id_regex: str


class ExcludeTypes(BaseModel):
    types: List[str]


Exclusions = Union[
    ExcludeTool,
    ExcludeToolRegex,
    ExcludeTypes,
]
OptionalExclusionList = Annotated[Optional[List[Exclusions]], Field(None)]


class Tool(BaseModel):
    content_type: Literal["tool"] = Field("tool", alias="type")
    id: str
    model_config = ConfigDict(populate_by_name=True)


class Label(BaseModel):
    content_type: Literal["label"] = Field(alias="type", default="label")
    id: Optional[str] = None
    text: str
    model_config = ConfigDict(populate_by_name=True)


class LabelShortcut(BaseModel):
    content_type: Literal["simple_label"] = "simple_label"
    label: str


class Workflow(BaseModel):
    content_type: Literal["workflow"] = Field(alias="type", default="workflow")
    id: str
    model_config = ConfigDict(populate_by_name=True)


class ItemsFrom(BaseModel):
    content_type: Literal["items_from"] = "items_from"
    items_from: str
    excludes: OptionalExclusionList


SectionContent = Union[
    Tool,
    Label,
    LabelShortcut,
    Workflow,
    ItemsFrom,
]


class HasItems:
    items: Optional[List[Any]]

    @property
    def items_expanded(self) -> Optional[List["ExpandedRootContent"]]:
        if self.items is None:
            return None

        # replace SectionAliases with individual SectionAlias objects
        # replace LabelShortcuts with Labels
        items: List[ExpandedRootContent] = []
        for item in self.items:
            item = cast(RootContent, item)
            if isinstance(item, SectionAliases):
                for section in item.sections:
                    section_alias = SectionAlias(
                        section=section,
                        excludes=item.excludes,
                    )
                    items.append(section_alias)
            elif isinstance(item, LabelShortcut):
                new_item = Label(
                    id=None,
                    text=item.label,
                    content_type="label",
                )
                items.append(new_item)
            else:
                items.append(item)
        return items


class Section(BaseModel, HasItems):
    content_type: Literal["section"] = Field(alias="type")
    id: Optional[str] = None
    name: Optional[str] = None
    items: Optional[List[SectionContent]] = None
    excludes: OptionalExclusionList
    model_config = ConfigDict(populate_by_name=True)


class SectionAlias(BaseModel):
    content_type: Literal["section_alias"] = "section_alias"
    section: str
    excludes: OptionalExclusionList = None


class SectionAliases(BaseModel):
    content_type: Literal["section_aliases"] = "section_aliases"
    sections: List[str]
    excludes: OptionalExclusionList = None


RootContent = Union[
    Section,
    SectionAlias,
    SectionAliases,
    Tool,
    Label,
    LabelShortcut,
    Workflow,
    ItemsFrom,
]

ExpandedRootContent = Union[
    Section,
    SectionAlias,
    Tool,
    Label,
    Workflow,
    ItemsFrom,
]


class StaticToolBoxView(BaseModel, HasItems):
    id: str
    name: str
    description: Optional[str] = None
    view_type: StaticToolBoxViewTypeEnum = Field(alias="type")
    items: Optional[List[RootContent]] = None  # if empty, use integrated tool panel
    excludes: OptionalExclusionList

    @staticmethod
    def from_dict(as_dict):
        return StaticToolBoxView(**as_dict)

    model_config = ConfigDict(populate_by_name=True)
