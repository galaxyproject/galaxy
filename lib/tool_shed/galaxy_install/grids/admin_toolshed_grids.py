import logging

from galaxy import util
from galaxy.model import tool_shed_install
from galaxy.web import url_for
from galaxy.web.framework.helpers import (
    grids,
    iff,
)
from tool_shed.util import repository_util

log = logging.getLogger(__name__)


def generate_deprecated_repository_img_str(include_mouse_over=False):
    if include_mouse_over:
        deprecated_tip_str = 'class="icon-button" title="This repository is deprecated in the Tool Shed"'
    else:
        deprecated_tip_str = ""
    return f"<img src=\"{url_for('/static')}/images/icon_error_sml.gif\" {deprecated_tip_str}/>"


def generate_includes_workflows_img_str(include_mouse_over=False):
    if include_mouse_over:
        deprecated_tip_str = 'class="icon-button" title="This repository contains exported workflows"'
    else:
        deprecated_tip_str = ""
    return f"<img src=\"{url_for('/static')}/images/fugue/gear.png\" {deprecated_tip_str}/>"


def generate_latest_revision_img_str(include_mouse_over=False):
    if include_mouse_over:
        latest_revision_tip_str = (
            'class="icon-button" title="This is the latest installable revision of this repository"'
        )
    else:
        latest_revision_tip_str = ""
    return f"<img src=\"{url_for('/static')}/style/ok_small.png\" {latest_revision_tip_str}/>"


def generate_revision_updates_img_str(include_mouse_over=False):
    if include_mouse_over:
        revision_updates_tip_str = (
            'class="icon-button" title="Updates are available in the Tool Shed for this revision"'
        )
    else:
        revision_updates_tip_str = ""
    return f"<img src=\"{url_for('/static')}/images/icon_warning_sml.gif\" {revision_updates_tip_str}/>"


def generate_revision_upgrades_img_str(include_mouse_over=False):
    if include_mouse_over:
        revision_upgrades_tip_str = (
            'class="icon-button" title="A newer installable revision is available for this repository"'
        )
    else:
        revision_upgrades_tip_str = ""
    return f"<img src=\"{url_for('/static')}/images/up.gif\" {revision_upgrades_tip_str}/>"


def generate_unknown_img_str(include_mouse_over=False):
    if include_mouse_over:
        unknown_tip_str = 'class="icon-button" title="Unable to get information from the Tool Shed"'
    else:
        unknown_tip_str = ""
    return f"<img src=\"{url_for('/static')}/style/question-octagon-frame.png\" {unknown_tip_str}/>"


class InstalledRepositoryGrid(grids.Grid):
    class ToolShedStatusColumn(grids.TextColumn):
        def get_value(self, trans, grid, tool_shed_repository):
            if tool_shed_repository.tool_shed_status:
                tool_shed_status_str = ""
                if tool_shed_repository.is_deprecated_in_tool_shed:
                    tool_shed_status_str += generate_deprecated_repository_img_str(include_mouse_over=True)
                if tool_shed_repository.is_latest_installable_revision:
                    tool_shed_status_str += generate_latest_revision_img_str(include_mouse_over=True)
                if tool_shed_repository.revision_update_available:
                    tool_shed_status_str += generate_revision_updates_img_str(include_mouse_over=True)
                if tool_shed_repository.upgrade_available:
                    tool_shed_status_str += generate_revision_upgrades_img_str(include_mouse_over=True)
                if tool_shed_repository.includes_workflows:
                    tool_shed_status_str += generate_includes_workflows_img_str(include_mouse_over=True)
            else:
                tool_shed_status_str = generate_unknown_img_str(include_mouse_over=True)
            return tool_shed_status_str

    class NameColumn(grids.TextColumn):
        def get_value(self, trans, grid, tool_shed_repository):
            return str(tool_shed_repository.name)

    class DescriptionColumn(grids.TextColumn):
        def get_value(self, trans, grid, tool_shed_repository):
            return util.unicodify(tool_shed_repository.description)

    class OwnerColumn(grids.TextColumn):
        def get_value(self, trans, grid, tool_shed_repository):
            return str(tool_shed_repository.owner)

    class RevisionColumn(grids.TextColumn):
        def get_value(self, trans, grid, tool_shed_repository):
            return str(tool_shed_repository.changeset_revision)

    class StatusColumn(grids.TextColumn):
        def get_value(self, trans, grid, tool_shed_repository):
            return repository_util.get_tool_shed_repository_status_label(trans.app, tool_shed_repository)

    class ToolShedColumn(grids.TextColumn):
        def get_value(self, trans, grid, tool_shed_repository):
            return tool_shed_repository.tool_shed

    class DeletedColumn(grids.DeletedColumn):
        def get_accepted_filters(self):
            """Returns a list of accepted filters for this column."""
            accepted_filter_labels_and_vals = {"Active": "False", "Deactivated or uninstalled": "True", "All": "All"}
            accepted_filters = []
            for label, val in accepted_filter_labels_and_vals.items():
                args = {self.key: val}
                accepted_filters.append(grids.GridColumnFilter(label, args))
            return accepted_filters

    # Grid definition
    title = "Installed tool shed repositories"
    model_class = tool_shed_install.ToolShedRepository
    default_sort_key = "name"
    columns = [
        ToolShedStatusColumn(label=""),
        NameColumn(
            label="Name",
            key="name",
            link=(
                lambda item: iff(
                    item.status in [tool_shed_install.ToolShedRepository.installation_status.CLONING],
                    None,
                    dict(controller="admin_toolshed", action="manage_repository", id=item.id),
                )
            ),
            target="center",
            attach_popup=True,
        ),
        DescriptionColumn(label="Description"),
        OwnerColumn(label="Owner"),
        RevisionColumn(label="Revision"),
        StatusColumn(label="Installation Status", filterable="advanced"),
        ToolShedColumn(label="Tool shed"),
        # Columns that are valid for filtering but are not visible.
        DeletedColumn(label="Status", key="deleted", visible=False, filterable="advanced"),
    ]
    columns.append(
        grids.MulticolFilterColumn(
            "Search repository name",
            cols_to_filter=[columns[1]],
            key="free-text-search",
            visible=False,
            filterable="standard",
        )
    )
    operations = [
        grids.GridOperation(
            label="Update tool shed status", condition=(lambda item: not item.deleted), allow_multiple=False
        ),
        grids.GridOperation(
            label="Get updates",
            condition=(
                lambda item: not item.deleted
                and item.revision_update_available
                and item.status
                not in [
                    tool_shed_install.ToolShedRepository.installation_status.ERROR,
                    tool_shed_install.ToolShedRepository.installation_status.NEW,
                ]
            ),
            allow_multiple=False,
            target="center",
            url_args=dict(controller="admin_toolshed", action="check_for_updates"),
        ),
        grids.GridOperation(
            label="Install latest revision",
            condition=(lambda item: item.upgrade_available),
            allow_multiple=False,
            target="center",
            url_args=dict(controller="admin_toolshed", action="install_latest_repository_revision"),
        ),
        grids.GridOperation(
            label="Install",
            condition=(
                lambda item: not item.deleted
                and item.status == tool_shed_install.ToolShedRepository.installation_status.NEW
            ),
            allow_multiple=False,
            target="center",
            url_args=dict(controller="admin_toolshed", action="manage_repository", operation="install"),
        ),
        grids.GridOperation(
            label="Deactivate or uninstall",
            condition=(
                lambda item: not item.deleted
                and item.status != tool_shed_install.ToolShedRepository.installation_status.NEW
            ),
            allow_multiple=True,
            target="center",
            url_args=dict(controller="admin_toolshed", action="deactivate_or_uninstall_repository"),
        ),
        grids.GridOperation(
            label="Activate or reinstall",
            condition=(lambda item: item.deleted),
            allow_multiple=False,
            target="center",
            url_args=dict(controller="admin_toolshed", action="restore_repository"),
        ),
        grids.GridOperation(
            label="Purge",
            condition=(lambda item: item.is_new),
            allow_multiple=False,
            target="center",
            url_args=dict(controller="admin_toolshed", action="purge_repository"),
        ),
    ]
    default_filter = dict(deleted="False")
    num_rows_per_page = 50
    use_paging = False

    def build_initial_query(self, trans, **kwd):
        return trans.install_model.context.query(self.model_class).order_by(
            self.model_class.table.c.tool_shed,
            self.model_class.table.c.name,
            self.model_class.table.c.owner,
            self.model_class.table.c.ctx_rev,
        )

    @property
    def legend(self):
        legend_str = f"{generate_revision_updates_img_str()}&nbsp;&nbsp;Updates are available in the Tool Shed for this revision<br/>"
        legend_str += f"{generate_revision_upgrades_img_str()}&nbsp;&nbsp;A newer installable revision is available for this repository<br/>"
        legend_str += f"{generate_latest_revision_img_str()}&nbsp;&nbsp;This is the latest installable revision of this repository<br/>"
        legend_str += (
            f"{generate_deprecated_repository_img_str()}&nbsp;&nbsp;This repository is deprecated in the Tool Shed<br/>"
        )
        legend_str += (
            f"{generate_includes_workflows_img_str()}&nbsp;&nbsp;This repository contains exported workflows<br/>"
        )
        legend_str += f"{generate_unknown_img_str()}&nbsp;&nbsp;Unable to get information from the Tool Shed<br/>"
        return legend_str
