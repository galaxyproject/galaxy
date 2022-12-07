import os
from typing import (
    Callable,
    Dict,
    Iterator,
    List,
    Optional,
    Tuple,
    Union,
)

from pydantic import (
    BaseModel,
    Extra,
    root_validator,
)

from galaxy.util import (
    asbool,
    Element,
)

ALLOW_EXTRA = Extra.forbid


DEFAULT_VALUE_TRANSLATION_TYPE = "template"
VALUE_TRANSLATION_FUNCTIONS: Dict[str, Callable] = dict(abspath=os.path.abspath)
DEFAULT_VALUE_TRANSLATION_TYPE = "template"


class DataTableBundleProcessorDataTableOutputColumnTranslation(BaseModel):
    type: str
    value: str

    class Config:
        extra = ALLOW_EXTRA


class DataTableBundleProcessorDataTableOutputColumnMove(BaseModel):
    type: str
    source_base: Optional[str] = None
    source_value: str = ""
    target_base: Optional[str] = None
    target_value: Optional[str] = None
    relativize_symlinks: bool

    class Config:
        extra = ALLOW_EXTRA


class DataTableBundleProcessorDataTableOutputColumn(BaseModel):
    name: str
    data_table_name: str
    output_ref: Optional[str] = None
    value_translations: List[DataTableBundleProcessorDataTableOutputColumnTranslation] = []
    moves: List[DataTableBundleProcessorDataTableOutputColumnMove] = []

    class Config:
        extra = ALLOW_EXTRA

    @root_validator(pre=True)
    def fill_in_default_data_table_name(cls, values):
        data_table_name = values.get("data_table_name")
        if data_table_name is None:
            values["data_table_name"] = values["name"]
        return values


class DataTableBundleProcessorDataTableOutput(BaseModel):
    columns: List[DataTableBundleProcessorDataTableOutputColumn]

    class Config:
        extra = ALLOW_EXTRA


class DataTableBundleProcessorDataTable(BaseModel):
    name: str
    output: Optional[DataTableBundleProcessorDataTableOutput]

    class Config:
        extra = ALLOW_EXTRA


class DataTableBundleProcessorDescription(BaseModel):
    undeclared_tables: bool = False
    data_tables: List[DataTableBundleProcessorDataTable]

    class Config:
        extra = ALLOW_EXTRA

    @property
    def data_table_names(self) -> List[str]:
        names = []
        for data_table in self.data_tables:
            data_table_name = data_table.name
            names.append(data_table_name)
        return names

    def _walk_columns(self) -> Iterator[Tuple[str, DataTableBundleProcessorDataTableOutputColumn]]:
        for data_table in self.data_tables:
            data_table_name = data_table.name
            output = data_table.output
            if output:
                for column in output.columns:
                    yield (data_table_name, column)

    @property
    def output_ref_by_data_table(self) -> Dict[str, Dict[str, str]]:
        output_refs: Dict[str, Dict[str, str]] = {}
        for data_table_name, column in self._walk_columns():
            data_table_column_name = column.data_table_name
            output_ref = column.output_ref
            if output_ref is not None:
                if data_table_name not in output_refs:
                    output_refs[data_table_name] = {}
                output_refs[data_table_name][data_table_column_name] = output_ref
        return output_refs

    @property
    def move_by_data_table_column(self) -> Dict[str, Dict[str, DataTableBundleProcessorDataTableOutputColumnMove]]:
        by_column: Dict[str, Dict[str, DataTableBundleProcessorDataTableOutputColumnMove]] = {}
        for data_table_name, column in self._walk_columns():
            data_table_column_name = column.data_table_name
            for move in column.moves:
                if data_table_name not in by_column:
                    by_column[data_table_name] = {}
                by_column[data_table_name][data_table_column_name] = move

        return by_column

    @property
    def value_translation_by_data_table_column(self) -> Dict[str, Dict[str, List[Union[str, Callable]]]]:
        by_column: Dict[str, Dict[str, List[Union[str, Callable]]]] = {}
        for data_table_name, column in self._walk_columns():
            data_table_column_name = column.data_table_name
            for value_translation_model in column.value_translations:
                value_translation_str = value_translation_model.value
                value_translation_type = value_translation_model.type
                if data_table_name not in by_column:
                    by_column[data_table_name] = {}
                if data_table_column_name not in by_column[data_table_name]:
                    by_column[data_table_name][data_table_column_name] = []
                value_translation: Union[str, Callable]
                if value_translation_type == "function":
                    if value_translation_str in VALUE_TRANSLATION_FUNCTIONS:
                        value_translation = VALUE_TRANSLATION_FUNCTIONS[value_translation_str]
                    else:
                        raise ValueError(f"Unsupported value translation function: '{value_translation}'")
                else:
                    assert value_translation_type == DEFAULT_VALUE_TRANSLATION_TYPE, ValueError(
                        f"Unsupported value translation type: '{value_translation_type}'"
                    )
                    value_translation = value_translation_str
                by_column[data_table_name][data_table_column_name].append(value_translation)
        return by_column


class RepoInfo(BaseModel):
    tool_shed: str
    name: str
    owner: str
    installed_changeset_revision: str

    class Config:
        # we use dictionary equality (yuk) so definitely make sure this is okay.
        extra = Extra.forbid


class DataTableBundle(BaseModel):
    processor_description: DataTableBundleProcessorDescription
    data_tables: dict
    output_name: Optional[str] = None
    repo_info: Optional[RepoInfo] = None


def _xml_to_data_table_output_column_move(move_elem: Element) -> DataTableBundleProcessorDataTableOutputColumnMove:
    move_type = move_elem.get("type", "directory")
    relativize_symlinks = move_elem.get(
        "relativize_symlinks", False
    )  # TODO: should we instead always relativize links?
    source_elem = move_elem.find("source")
    if source_elem is None:
        source_base = None
        source_value = ""
    else:
        source_base = source_elem.get("base", None)
        source_value = source_elem.text
    target_elem = move_elem.find("target")
    if target_elem is None:
        target_base = None
        target_value = ""
    else:
        target_base = target_elem.get("base", None)
        target_value = target_elem.text
    return DataTableBundleProcessorDataTableOutputColumnMove(
        type=move_type,
        source_base=source_base,
        source_value=source_value,
        target_base=target_base,
        target_value=target_value,
        relativize_symlinks=relativize_symlinks,
    )


def _xml_to_data_table_output_column_translation(
    value_translation_elem: Element,
) -> Optional[DataTableBundleProcessorDataTableOutputColumnTranslation]:
    value_translation = value_translation_elem.text
    if value_translation is not None:
        value_translation_type = value_translation_elem.get("type", DEFAULT_VALUE_TRANSLATION_TYPE)
        return DataTableBundleProcessorDataTableOutputColumnTranslation(
            value=value_translation, type=value_translation_type
        )
    else:
        return None


def _xml_to_data_table_output_column(column_elem: Element) -> DataTableBundleProcessorDataTableOutputColumn:
    column_name = column_elem.get("name", None)
    assert column_name is not None, "Name is required for column entry"
    data_table_column_name = column_elem.get("data_table_name", column_name)
    output_ref = column_elem.get("output_ref", None)
    value_translation_elems = column_elem.findall("value_translation")
    value_translations = []
    if value_translation_elems is not None:
        for value_translation_elem in value_translation_elems:
            value_translation = _xml_to_data_table_output_column_translation(value_translation_elem)
            if value_translation is None:
                continue
            value_translations.append(value_translation)

    moves = []
    for move_elem in column_elem.findall("move"):
        moves.append(_xml_to_data_table_output_column_move(move_elem))

    return DataTableBundleProcessorDataTableOutputColumn(
        name=column_name,
        data_table_name=data_table_column_name,
        output_ref=output_ref,
        value_translations=value_translations,
        moves=moves,
    )


def _xml_to_data_table_output(output_elem: Optional[Element]) -> Optional[DataTableBundleProcessorDataTableOutput]:
    if output_elem is not None:
        columns = []
        for column_elem in output_elem.findall("column"):
            columns.append(_xml_to_data_table_output_column(column_elem))
        return DataTableBundleProcessorDataTableOutput(columns=columns)
    else:
        return None


def _xml_to_data_table(data_table_elem: Element) -> DataTableBundleProcessorDataTable:
    data_table_name = data_table_elem.get("name")
    assert data_table_name is not None, "A name is required for a data table entry"

    output_elem = data_table_elem.find("output")
    output = _xml_to_data_table_output(output_elem)
    return DataTableBundleProcessorDataTable(name=data_table_name, output=output)


def convert_data_tables_xml(elem: Element) -> DataTableBundleProcessorDescription:
    undeclared_tables = asbool(elem.get("undeclared_tables", False))
    data_tables = []
    for data_table_elem in elem.findall("data_table"):
        data_tables.append(_xml_to_data_table(data_table_elem))

    return DataTableBundleProcessorDescription(undeclared_tables=undeclared_tables, data_tables=data_tables)
