from enum import Enum
from typing import Any, cast, List, Optional, Union

from pydantic import BaseModel, Field
from typing_extensions import Literal


class StaticToolBoxViewTypeEnum(str, Enum):
    generic = 'generic'
    activity = 'activity'
    publication = 'publication'
    training = 'training'


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
OptionalExclusionList = Optional[List[Exclusions]]


class Tool(BaseModel):
    content_type: Literal['tool'] = Field("tool", alias="type")
    id: str

    class Config:
        allow_population_by_field_name = True


class Label(BaseModel):
    content_type: Literal['label'] = Field(alias="type")
    id: Optional[str]
    text: str

    class Config:
        allow_population_by_field_name = True


class LabelShortcut(BaseModel):
    content_type = "simple_label"
    label: str


class Workflow(BaseModel):
    content_type: Literal['workflow'] = Field(alias="type")
    id: str

    class Config:
        allow_population_by_field_name = True


class ItemsFrom(BaseModel):
    content_type = "items_from"
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
    def items_expanded(self) -> Optional[List['ExpandedRootContent']]:
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
    content_type: Literal['section'] = Field(alias="type")
    id: Optional[str]
    name: Optional[str]
    items: Optional[List[SectionContent]]
    excludes: OptionalExclusionList

    class Config:
        allow_population_by_field_name = True


class SectionAlias(BaseModel):
    content_type = "section_alias"
    section: str
    excludes: OptionalExclusionList


class SectionAliases(BaseModel):
    content_type = "section_aliases"
    sections: List[str]
    excludes: OptionalExclusionList


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
    description: Optional[str]
    view_type: StaticToolBoxViewTypeEnum = Field(alias="type")
    items: Optional[List[RootContent]]  # if empty, use integrated tool panel
    excludes: OptionalExclusionList

    @staticmethod
    def from_dict(as_dict):
        return StaticToolBoxView(**as_dict)

    class Config:
        allow_population_by_field_name = True
