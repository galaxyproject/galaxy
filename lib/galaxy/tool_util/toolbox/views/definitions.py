from enum import Enum
from typing import (
    Any,
    cast,
    Literal,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
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
    types: list[str]


Exclusions = ExcludeTool | ExcludeToolRegex | ExcludeTypes
OptionalExclusionList = list[Exclusions] | None


class Tool(BaseModel):
    content_type: Literal["tool"] = Field("tool", alias="type")
    id: str
    model_config = ConfigDict(populate_by_name=True)


class Label(BaseModel):
    content_type: Literal["label"] = Field(alias="type", default="label")
    id: str | None = None
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
    excludes: OptionalExclusionList = None


SectionContent = Tool | Label | LabelShortcut | Workflow | ItemsFrom


class HasItems:
    items: list[Any] | None

    @property
    def items_expanded(self) -> list["ExpandedRootContent"] | None:
        if self.items is None:
            return None

        # replace SectionAliases with individual SectionAlias objects
        # replace LabelShortcuts with Labels
        items: list[ExpandedRootContent] = []
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
    id: str | None = None
    name: str | None = None
    items: list[SectionContent] | None = None
    excludes: OptionalExclusionList = None
    model_config = ConfigDict(populate_by_name=True)


class SectionAlias(BaseModel):
    content_type: Literal["section_alias"] = "section_alias"
    section: str
    excludes: OptionalExclusionList = None


class SectionAliases(BaseModel):
    content_type: Literal["section_aliases"] = "section_aliases"
    sections: list[str]
    excludes: OptionalExclusionList = None


RootContent = Section | SectionAlias | SectionAliases | Tool | Label | LabelShortcut | Workflow | ItemsFrom

ExpandedRootContent = Section | SectionAlias | Tool | Label | Workflow | ItemsFrom


class StaticToolBoxView(BaseModel, HasItems):
    id: str
    name: str
    description: str | None = None
    view_type: StaticToolBoxViewTypeEnum = Field(alias="type")
    items: list[RootContent] | None = None  # if empty, use integrated tool panel
    excludes: OptionalExclusionList = None

    @staticmethod
    def from_dict(as_dict):
        return StaticToolBoxView(**as_dict)

    model_config = ConfigDict(populate_by_name=True)
