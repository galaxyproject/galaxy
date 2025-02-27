import logging

from galaxy.tool_shed.tools.data_table_manager import (
    BaseShedToolDataTableManager,
    RequiredAppT,
)
from galaxy.tool_shed.util import (
    basic_util,
    hg_util,
)
from galaxy.tool_util.fetcher import ToolLocationFetcher
from galaxy.tool_util.parser import get_tool_source
from galaxy.tools import (
    create_tool_from_source,
    parameters,
)
from galaxy.tools.parameters import dynamic_options

log = logging.getLogger(__name__)


class ToolValidator:
    def __init__(self, app: RequiredAppT):
        self.app = app
        self.stdtm = BaseShedToolDataTableManager(self.app)

    def check_tool_input_params(self, repo_dir, tool_config_name, tool, sample_files):
        """
        Check all of the tool's input parameters, looking for any that are dynamically
        generated using external data files to make sure the files exist.
        """
        invalid_files_and_errors_tups = []
        for input_param in tool.input_params:
            if isinstance(input_param, parameters.basic.SelectToolParameter) and input_param.is_dynamic:
                # If the tool refers to .loc files or requires an entry in the tool_data_table_conf.xml,
                # make sure all requirements exist.
                options = input_param.dynamic_options or input_param.options
                if options and isinstance(options, dynamic_options.DynamicOptions):
                    if options.tool_data_table or options.missing_tool_data_table_name:
                        # Make sure the repository contains a tool_data_table_conf.xml.sample file.
                        sample_tool_data_table_conf = hg_util.get_config_from_disk(
                            "tool_data_table_conf.xml.sample", repo_dir
                        )
                        if sample_tool_data_table_conf:
                            error, correction_msg = self.stdtm.handle_sample_tool_data_table_conf_file(
                                sample_tool_data_table_conf, persist=False
                            )
                            if error:
                                invalid_files_and_errors_tups.append(
                                    ("tool_data_table_conf.xml.sample", correction_msg)
                                )
                        else:
                            correction_msg = "This file requires an entry in the tool_data_table_conf.xml file.  "
                            correction_msg += "Upload a file named tool_data_table_conf.xml.sample to the repository "
                            correction_msg += "that includes the required entry to correct this error.<br/>"
                            invalid_tup = (tool_config_name, correction_msg)
                            if invalid_tup not in invalid_files_and_errors_tups:
                                invalid_files_and_errors_tups.append(invalid_tup)
                    if options.index_file or options.tool_data_table and options.tool_data_table.missing_index_file:
                        # Make sure the repository contains the required xxx.loc.sample file.
                        index_file = options.index_file or options.tool_data_table.missing_index_file
                        index_file_name = basic_util.strip_path(index_file)
                        sample_found = False
                        for sample_file in sample_files:
                            sample_file_name = basic_util.strip_path(sample_file)
                            if sample_file_name == f"{index_file_name}.sample":
                                options.index_file = index_file_name
                                if options.tool_data_table:
                                    options.tool_data_table.missing_index_file = None
                                sample_found = True
                                break
                        if not sample_found:
                            correction_msg = (
                                f"This file refers to a file named <b>{index_file_name}</b>.  "
                                f"Upload a file named <b>{index_file_name}.sample</b> to the repository to correct this error."
                            )
                            invalid_files_and_errors_tups.append((tool_config_name, correction_msg))
        return invalid_files_and_errors_tups

    def load_tool_from_config(self, repository_id, full_path):
        tool_source = get_tool_source(
            full_path,
            enable_beta_formats=getattr(self.app.config, "enable_beta_tool_formats", False),
            tool_location_fetcher=ToolLocationFetcher(),
        )
        try:
            tool = create_tool_from_source(
                config_file=full_path,
                app=self.app,
                tool_source=tool_source,
                repository_id=repository_id,
                allow_code_files=False,
            )
            valid = True
            error_message = None
        except KeyError as e:
            tool = None
            valid = False
            error_message = (
                f'This file requires an entry for "{str(e)}" in the tool_data_table_conf.xml file. Upload a file '
            )
            error_message += (
                "named tool_data_table_conf.xml.sample to the repository that includes the required entry to correct "
            )
            error_message += "this error.  "
            log.exception(error_message)
        except Exception as e:
            tool = None
            valid = False
            error_message = str(e)
            log.exception("Caught exception loading tool from %s:", full_path)
        return tool, valid, error_message
