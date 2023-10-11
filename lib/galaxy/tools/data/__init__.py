"""
extend base tool data table implementations with special implementations
requiring full Galaxy dependencies (specifically the refgenie configuration
client currently).
"""

import logging
from typing import (
    Any,
    Dict,
    List,
    Type,
)

import refgenconf

from galaxy import util
from galaxy.tool_util.data import (
    TabularToolDataField,
    TabularToolDataTable,
    tool_data_table_types_list as tool_util_tool_data_table_types_list,
    ToolDataTable,
    ToolDataTableManager as BaseToolDataTableManager,
)
from galaxy.util.template import fill_template

log = logging.getLogger(__name__)


def table_from_dict(d: Dict[str, Any]) -> ToolDataTable:
    data_table_class = globals()[d["model_class"]]
    data_table = data_table_class.__new__(data_table_class)
    for attr, val in d.items():
        if not attr == "model_class":
            setattr(data_table, attr, val)
    data_table._loaded_content_version = 1
    return data_table


def from_dict(d: Dict[str, Any]) -> "ToolDataTableManager":
    tdtm = ToolDataTableManager.__new__(ToolDataTableManager)
    tdtm.data_tables = {name: table_from_dict(data) for name, data in d.items()}
    return tdtm


class RefgenieToolDataTable(TabularToolDataTable):
    """
    Data stored in refgenie

    .. code-block:: xml

        <table name="all_fasta" type="refgenie" asset="fasta" >
            <file path="refgenie.yml" />
            <field name="value" template="true">${__REFGENIE_UUID__}</field>
            <field name="dbkey" template="true">${__REFGENIE_GENOME__}</field>
            <field name="name" template="true">${__REFGENIE_DISPLAY_NAME__}</field>
            <field name="path" template="true">${__REFGENIE_ASSET__}</field>
        </table>
    """

    dict_collection_visible_keys = ["name"]
    dict_element_visible_keys = ["name", "fields"]
    dict_export_visible_keys = ["name", "data", "rg_asset", "largest_index", "columns", "missing_index_file"]

    type_key = "refgenie"

    def __init__(
        self,
        config_element,
        tool_data_path,
        tool_data_path_files,
        from_shed_config=False,
        filename=None,
        other_config_dict=None,
    ) -> None:
        super().__init__(
            config_element,
            tool_data_path,
            tool_data_path_files,
            from_shed_config,
            filename,
            other_config_dict=other_config_dict,
        )
        self.config_element = config_element
        self.data: List[List[str]] = []
        self.configure_and_load(config_element, tool_data_path, from_shed_config)

    def configure_and_load(self, config_element, tool_data_path, from_shed_config=False, url_timeout=10):
        self.rg_asset = config_element.get("asset", None)
        assert self.rg_asset, ValueError("You must specify an asset attribute.")
        super().configure_and_load(
            config_element, tool_data_path, from_shed_config=from_shed_config, url_timeout=url_timeout
        )

    def parse_column_spec(self, config_element):
        self.columns = {}
        self.key_map = {}
        self.template_for_column = {}
        self.strip_for_column = {}
        self.largest_index = 0
        for i, elem in enumerate(config_element.findall("field")):
            name = elem.get("name", None)
            assert name, ValueError("You must provide a name refgenie field element.")
            value = elem.text
            self.key_map[name] = value
            column_index = int(elem.get("column_index", i))

            empty_field_value = elem.get("empty_field_value", None)
            if empty_field_value is not None:
                self.empty_field_values[name] = empty_field_value

            self.template_for_column[name] = util.asbool(elem.get("template", False))
            self.strip_for_column[name] = util.asbool(elem.get("strip", False))

            self.columns[name] = column_index
            self.largest_index = max(self.largest_index, column_index)
        if "name" not in self.columns:
            self.columns["name"] = self.columns["value"]

    def parse_file_fields(self, filename, errors=None, here="__HERE__"):
        try:
            rgc = refgenconf.RefGenConf(filename, writable=False, skip_read_lock=True)
        except refgenconf.exceptions.RefgenconfError as e:
            log.error('Unable to load refgenie config file "%s": %s', filename, e)
            if errors is not None:
                errors.append(e)
            return []
        rval = []
        for genome in rgc.list_genomes_by_asset(self.rg_asset):
            genome_attributes = rgc.get_genome_attributes(genome)
            genome_description = genome_attributes.get("genome_description", None)
            asset_list = rgc.list(genome, include_tags=True)[genome]
            for tagged_asset in asset_list:
                asset, tag = tagged_asset.rsplit(":", 1)
                if asset != self.rg_asset:
                    continue
                digest = rgc.id(genome, asset, tag=tag)
                uuid = f"refgenie:{genome}/{self.rg_asset}:{tag}@{digest}"
                if genome_description:
                    display_name = f"{genome_description} (refgenie: {genome}@{digest})"
                else:
                    display_name = f"{genome}/{tagged_asset}@{digest}"

                def _seek_key(key):
                    return rgc.seek(genome, asset, tag_name=tag, seek_key=key)  # noqa: B023

                template_dict = {
                    "__REFGENIE_UUID__": uuid,
                    "__REFGENIE_GENOME__": genome,
                    "__REFGENIE_TAG__": tag,
                    "__REFGENIE_DISPLAY_NAME__": display_name,
                    "__REFGENIE_ASSET__": rgc.seek(genome, asset, tag_name=tag),
                    "__REFGENIE_ASSET_NAME__": asset,
                    "__REFGENIE_DIGEST__": digest,
                    "__REFGENIE_GENOME_ATTRIBUTES__": genome_attributes,
                    "__REFGENIE__": rgc,
                    "__REFGENIE_SEEK_KEY__": _seek_key,
                }
                fields = [""] * (self.largest_index + 1)
                for name, index in self.columns.items():
                    rg_value = self.key_map[name]
                    # Default is hard-coded value
                    if self.template_for_column.get(name, False):
                        rg_value = fill_template(rg_value, template_dict)
                    if self.strip_for_column.get(name, False):
                        rg_value = rg_value.strip()
                    fields[index] = rg_value
                rval.append(fields)
        log.debug(
            "Loaded %i entries from refgenie '%s' asset '%s' for '%s'", len(rval), filename, self.rg_asset, self.name
        )
        return rval

    def _remove_entry(self, values):
        log.warning(
            "Deletion from refgenie-backed '%s' data table is not supported, will only try to delete from .loc files",
            self.name,
        )

        # Update every non-refgenie files
        super()._remove_entry(values)


# Registry of tool data types by type_key
tool_data_table_types_list: List[Type[ToolDataTable]] = tool_util_tool_data_table_types_list + [RefgenieToolDataTable]
tool_data_table_types = {cls.type_key: cls for cls in tool_data_table_types_list}


class ToolDataTableManager(BaseToolDataTableManager):
    tool_data_table_types = {cls.type_key: cls for cls in tool_data_table_types_list}


__all__ = (
    "RefgenieToolDataTable",
    "TabularToolDataField",
    "TabularToolDataTable",
    "ToolDataTable",
    "ToolDataTableManager",
    "tool_data_table_types",
)
