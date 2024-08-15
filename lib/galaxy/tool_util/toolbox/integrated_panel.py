import logging
import os
import shutil
import string
import time
import traceback
from xml.sax.saxutils import escape

from galaxy.util import RW_R__R__
from galaxy.util.renamed_temporary_file import RenamedTemporaryFile
from .panel import (
    panel_item_types,
    ToolPanelElements,
)

log = logging.getLogger(__name__)

INTEGRATED_TOOL_PANEL_DESCRIPTION = """
This is Galaxy's integrated tool panel and should be modified directly only for
reordering tools inside a section. Each time Galaxy starts up, this file is
synchronized with the various tool config files: tools, sections and labels
added to one of these files, will be added also here in the appropriate place,
while elements removed from the tool config files will be correspondingly
deleted from this file.
To modify locally managed tools (e.g. from tool_conf.xml) modify that file
directly and restart Galaxy. Whenever possible Tool Shed managed tools (e.g.
from shed_tool_conf.xml) should be managed from within the Galaxy interface or
via its API - but if changes are necessary (such as to hide a tool or re-assign
its section) modify that file and restart Galaxy.
"""


class ManagesIntegratedToolPanelMixin:
    def _init_integrated_tool_panel(self, config):
        self.update_integrated_tool_panel = config.update_integrated_tool_panel
        self._integrated_tool_panel_config = config.integrated_tool_panel_config
        self._integrated_tool_panel_tracking_directory = getattr(
            config, "integrated_tool_panel_tracking_directory", None
        )
        # In-memory dictionary that defines the layout of the tool_panel.xml file on disk.
        self._integrated_tool_panel = ToolPanelElements()
        self._integrated_tool_panel_config_has_contents = (
            os.path.exists(self._integrated_tool_panel_config)
            and os.stat(self._integrated_tool_panel_config).st_size > 0
        )
        if self._integrated_tool_panel_config_has_contents:
            self._load_integrated_tool_panel_keys()

    def _save_integrated_tool_panel(self):
        if self.update_integrated_tool_panel:
            # Write the current in-memory integrated_tool_panel to the integrated_tool_panel.xml file.
            # This will cover cases where the Galaxy administrator manually edited one or more of the tool panel
            # config files, adding or removing locally developed tools or workflows.  The value of integrated_tool_panel
            # will be False when things like functional tests are the caller.
            self._write_integrated_tool_panel_config_file()

    def _write_integrated_tool_panel_config_file(self):
        """
        Write the current in-memory version of the integrated_tool_panel.xml file to disk.  Since Galaxy administrators
        use this file to manage the tool panel, we'll not use xml_to_string() since it doesn't write XML quite right.
        """
        destination = os.path.abspath(self._integrated_tool_panel_config)
        log.debug("Writing integrated tool panel config file to '%s'", destination)
        tracking_directory = self._integrated_tool_panel_tracking_directory
        if tracking_directory:
            if not os.path.exists(tracking_directory):
                os.makedirs(tracking_directory)
            name = f"integrated_tool_panel_{time.time():.10f}.xml"
            filename = os.path.join(tracking_directory, name)
        else:
            filename = destination
        template = string.Template(
            """<?xml version="1.0"?>
<toolbox>
    <!--
    $INTEGRATED_TOOL_PANEL_DESCRIPTION
    -->
$INTEGRATED_TOOL_PANEL
</toolbox>
"""
        )
        integrated_tool_panel = []
        for _, item_type, item in self._integrated_tool_panel.panel_items_iter():
            if item:
                if item_type == panel_item_types.TOOL:
                    integrated_tool_panel.append(f'    <tool id="{item.id}" />\n')
                elif item_type == panel_item_types.WORKFLOW:
                    integrated_tool_panel.append(f'    <workflow id="{item.id}" />\n')
                elif item_type == panel_item_types.LABEL:
                    label_id = item.id or ""
                    label_text = item.text or ""
                    label_version = item.version or ""
                    integrated_tool_panel.append(
                        f'    <label id="{label_id}" text="{label_text}" version="{label_version}" />\n'
                    )
                elif item_type == panel_item_types.SECTION:
                    section_id = item.id or ""
                    section_name = item.name or ""
                    section_version = item.version or ""
                    integrated_tool_panel.append(
                        f'    <section id="{escape(section_id)}" name="{escape(section_name)}" version="{section_version}">\n'
                    )
                    for _section_key, section_item_type, section_item in item.panel_items_iter():
                        if section_item_type == panel_item_types.TOOL:
                            if section_item:
                                integrated_tool_panel.append(f'        <tool id="{section_item.id}" />\n')
                        elif section_item_type == panel_item_types.WORKFLOW:
                            if section_item:
                                integrated_tool_panel.append(f'        <workflow id="{section_item.id}" />\n')
                        elif section_item_type == panel_item_types.LABEL:
                            if section_item:
                                label_id = section_item.id or ""
                                label_text = section_item.text or ""
                                label_version = section_item.version or ""
                                integrated_tool_panel.append(
                                    f'        <label id="{label_id}" text="{label_text}" version="{label_version}" />\n'
                                )
                    integrated_tool_panel.append("    </section>\n")
        tool_panel_description = "\n    ".join(line for line in INTEGRATED_TOOL_PANEL_DESCRIPTION.split("\n") if line)
        tp_string = template.substitute(
            INTEGRATED_TOOL_PANEL_DESCRIPTION=tool_panel_description,
            INTEGRATED_TOOL_PANEL="\n".join(integrated_tool_panel),
        )
        with RenamedTemporaryFile(filename, mode="w") as f:
            f.write(tp_string)
        if tracking_directory:
            with open(f"{filename}.stack", "w") as f:
                f.write("".join(traceback.format_stack()))
            shutil.copy(filename, f"{filename}.copy")
            shutil.move(f"{filename}.copy", destination)
        try:
            os.chmod(destination, RW_R__R__)
        except OSError:
            # That can happen if multiple threads are simultaneously moving/chmod'ing this file
            # Should be harmless, though this race condition should be avoided.
            pass
