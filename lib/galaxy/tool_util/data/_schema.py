from typing import (
    Dict,
    List,
    Optional,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
)


class Model(BaseModel):
    model_config = ConfigDict(protected_namespaces=())


class ToolDataEntry(Model):
    name: str = Field(
        ...,  # Mark this field as required
        title="Name",
        description="The name of this tool data entry",
        examples=["all_fasta"],
    )
    model_class: str = Field(
        ...,  # Mark this field as required
        title="Model class",
        description="The name of class modelling this tool data",
        examples=["TabularToolDataTable"],
    )


class ToolDataEntryList(RootModel):
    root: List[ToolDataEntry] = Field(
        title="A list with details on individual data tables.",
    )

    def find_entry(self, name: str) -> Optional[ToolDataEntry]:
        for entry in self.root:
            if entry.name == name:
                return entry
        return None


class ToolDataDetails(ToolDataEntry):
    columns: List[str] = Field(
        ...,  # Mark this field as required
        title="Columns",
        description="A list of column names",
        examples=["value", "dbkey", "name", "path"],
    )
    # We must use an alias since the name 'fields'
    # shadows a Model attribute
    fields_value: List[List[str]] = Field(
        alias="fields",
        default=[],
        title="Fields",
        description="",  # TODO add documentation
    )


class ToolDataField(Model):
    name: str = Field(
        ...,  # Mark this field as required
        title="Name",
        description="The name of the field",
    )
    model_class: str = Field(
        ...,  # Mark this field as required
        title="Model class",
        description="The name of class modelling this tool data field",
        examples=["TabularToolDataField"],
    )
    # We must use an alias since the name 'fields'
    # shadows a Model attribute
    fields_value: Dict[str, str] = Field(
        ...,  # Mark this field as required
        alias="fields",
        title="Fields",
        description="",  # TODO add documentation
    )
    base_dir: List[str] = Field(
        ...,  # Mark this field as required
        title="Base directories",
        description="A list of directories where the data files are stored",
    )
    files: Dict[str, int] = Field(
        ...,  # Mark this field as required
        title="Files",
        description="A dictionary of file names and their size in bytes",
        examples=[{"file.txt": 136}],
    )
    fingerprint: str = Field(
        ...,  # Mark this field as required
        title="Fingerprint",
        description="SHA1 Hash",
        examples=["22b45237a85c2b3f474bf66888c534387ffe0ced"],
    )


class ToolDataItem(Model):
    values: str = Field(
        ...,  # Mark this field as required
        title="Values",
        description=(
            "A `\\t` (TAB) separated list of column __contents__."
            " You must specify a value for each of the columns of the data table."
        ),
        examples=["value\tdbkey\tname\tpath"],
    )
