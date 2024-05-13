import json
import logging

from markupsafe import escape as escape_html
from sqlalchemy import (
    and_,
    false,
    or_,
    true,
)

import tool_shed.grids.util as grids_util
import tool_shed.repository_types.util as rt_util
import tool_shed.util.shed_util_common as suc
from galaxy.web.legacy_framework import grids
from tool_shed.util import (
    hg_util,
    metadata_util,
    repository_util,
)
from tool_shed.webapp import model

log = logging.getLogger(__name__)


class CategoryGrid(grids.Grid):
    class NameColumn(grids.TextColumn):
        def get_value(self, trans, grid, category):
            return category.name

    class DescriptionColumn(grids.TextColumn):
        def get_value(self, trans, grid, category):
            return category.description

    class RepositoriesColumn(grids.TextColumn):
        def get_value(self, trans, grid, category):
            category_name = str(category.name)
            filter = trans.app.repository_grid_filter_manager.get_filter(trans)
            if filter == trans.app.repository_grid_filter_manager.filters.CERTIFIED_LEVEL_ONE:
                return (
                    trans.app.repository_registry.certified_level_one_viewable_repositories_and_suites_by_category.get(
                        category_name, 0
                    )
                )
            elif filter == trans.app.repository_grid_filter_manager.filters.CERTIFIED_LEVEL_ONE_SUITES:
                return trans.app.repository_registry.certified_level_one_viewable_suites_by_category.get(
                    category_name, 0
                )
            elif filter == trans.app.repository_grid_filter_manager.filters.SUITES:
                return trans.app.repository_registry.viewable_suites_by_category.get(category_name, 0)
            else:
                # The value filter is None.
                return trans.app.repository_registry.viewable_repositories_and_suites_by_category.get(category_name, 0)

    title = "Categories"
    model_class = model.Category
    template = "/webapps/tool_shed/category/grid.mako"
    default_sort_key = "name"
    columns = [
        NameColumn(
            "Name",
            key="Category.name",
            link=(lambda item: dict(operation="repositories_by_category", id=item.id)),
            attach_popup=False,
        ),
        DescriptionColumn("Description", key="Category.description", attach_popup=False),
        RepositoriesColumn("Repositories", model_class=model.Repository, attach_popup=False),
    ]
    # Override these
    num_rows_per_page = 50


class RepositoryGrid(grids.Grid):
    class NameColumn(grids.TextColumn):
        def get_value(self, trans, grid, repository):
            return escape_html(repository.name)

    class TypeColumn(grids.TextColumn):
        def get_value(self, trans, grid, repository):
            type_class = repository.get_type_class(trans.app)
            return escape_html(type_class.label)

    class HeadsColumn(grids.GridColumn):
        def __init__(self, col_name):
            grids.GridColumn.__init__(self, col_name)

        def get_value(self, trans, grid, repository):
            """Display the current repository heads."""
            repo = repository.hg_repo
            heads = hg_util.get_repository_heads(repo)
            multiple_heads = len(heads) > 1
            if multiple_heads:
                heads_str = '<font color="red">'
            else:
                heads_str = ""
            for ctx in heads:
                heads_str += f"{hg_util.get_revision_label_from_ctx(ctx, include_date=True)}<br/>"
            heads_str.rstrip("<br/>")
            if multiple_heads:
                heads_str += "</font>"
            return heads_str

    class MetadataRevisionColumn(grids.GridColumn):
        def __init__(self, col_name):
            grids.GridColumn.__init__(self, col_name)

        def get_value(self, trans, grid, repository):
            """Display a SelectField whose options are the changeset_revision strings of all metadata revisions of this repository."""
            # A repository's metadata revisions may not all be installable, as some may contain only invalid tools.
            select_field = grids_util.build_changeset_revision_select_field(trans, repository, downloadable=False)
            if len(select_field.options) > 1:
                tmpl = f"<select name='{select_field.name}'>"
                for o in select_field.options:
                    tmpl += f"<option value='{o[1]}'>{o[0]}</option>"
                tmpl += "</select>"
                return tmpl
            elif len(select_field.options) == 1:
                option_items = select_field.options[0][0]
                rev_label, rev_date = option_items.split(" ")
                rev_date = f'<i><font color="#666666">{rev_date}</font></i>'
                return f"{rev_label} {rev_date}"
            return ""

    class LatestInstallableRevisionColumn(grids.GridColumn):
        def __init__(self, col_name):
            grids.GridColumn.__init__(self, col_name)

        def get_value(self, trans, grid, repository):
            """Display the latest installable revision label (may not be the repository tip)."""
            select_field = grids_util.build_changeset_revision_select_field(trans, repository, downloadable=False)
            if select_field.options:
                return select_field.options[0][0]
            return ""

    class TipRevisionColumn(grids.GridColumn):
        def __init__(self, col_name):
            grids.GridColumn.__init__(self, col_name)

        def get_value(self, trans, grid, repository):
            """Display the repository tip revision label."""
            return escape_html(repository.revision())

    class DescriptionColumn(grids.TextColumn):
        def get_value(self, trans, grid, repository):
            return escape_html(repository.description)

    class CategoryColumn(grids.TextColumn):
        def get_value(self, trans, grid, repository):
            rval = "<ul>"
            if repository.categories:
                for rca in repository.categories:
                    rval += f'<li><a href="browse_repositories?operation=repositories_by_category&id={trans.security.encode_id(rca.category.id)}">{rca.category.name}</a></li>'
            else:
                rval += "<li>not set</li>"
            rval += "</ul>"
            return rval

    class RepositoryCategoryColumn(grids.GridColumn):
        def filter(self, trans, user, query, column_filter):
            """Modify query to filter by category."""
            if column_filter == "All":
                return query
            return query.filter(model.Category.name == column_filter)

    class UserColumn(grids.TextColumn):
        def get_value(self, trans, grid, repository):
            if repository.user:
                return escape_html(repository.user.username)
            return "no user"

    class EmailColumn(grids.TextColumn):
        def filter(self, trans, user, query, column_filter):
            if column_filter == "All":
                return query
            return query.filter(
                and_(
                    model.Repository.table.c.user_id == model.User.table.c.id, model.User.table.c.email == column_filter
                )
            )

    class EmailAlertsColumn(grids.TextColumn):
        def get_value(self, trans, grid, repository):
            if trans.user and repository.email_alerts and trans.user.email in json.loads(repository.email_alerts):
                return "yes"
            return ""

    class DeprecatedColumn(grids.TextColumn):
        def get_value(self, trans, grid, repository):
            if repository.deprecated:
                return "yes"
            return ""

    title = "Repositories"
    model_class = model.Repository
    default_sort_key = "name"
    use_hide_message = False
    columns = [
        NameColumn(
            "Name",
            key="name",
            link=(lambda item: dict(operation="view_or_manage_repository", id=item.id)),
            attach_popup=False,
        ),
        DescriptionColumn("Synopsis", key="description", attach_popup=False),
        TypeColumn("Type"),
        MetadataRevisionColumn("Metadata<br/>Revisions"),
        UserColumn(
            "Owner",
            model_class=model.User,
            link=(lambda item: dict(operation="repositories_by_user", id=item.id)),
            attach_popup=False,
            key="User.username",
        ),
        # Columns that are valid for filtering but are not visible.
        EmailColumn("Email", model_class=model.User, key="email", visible=False),
        RepositoryCategoryColumn("Category", model_class=model.Category, key="Category.name", visible=False),
    ]
    columns.append(
        grids.MulticolFilterColumn(
            "Search repository name, description",
            cols_to_filter=[columns[0], columns[1]],
            key="free-text-search",
            visible=False,
            filterable="standard",
        )
    )
    default_filter = dict(deleted="False")
    num_rows_per_page = 50
    use_paging = True
    allow_fetching_all_results = False

    def build_initial_query(self, trans, **kwd):
        filter = trans.app.repository_grid_filter_manager.get_filter(trans)
        if filter == trans.app.repository_grid_filter_manager.filters.CERTIFIED_LEVEL_ONE:
            return (
                trans.sa_session.query(model.Repository)
                .join(model.RepositoryMetadata.table)
                .filter(or_(*trans.app.repository_registry.certified_level_one_clause_list))
                .join(model.User.table)
                .outerjoin(model.RepositoryCategoryAssociation)
                .outerjoin(model.Category.table)
            )
        if filter == trans.app.repository_grid_filter_manager.filters.CERTIFIED_LEVEL_ONE_SUITES:
            return (
                trans.sa_session.query(model.Repository)
                .filter(model.Repository.type == rt_util.REPOSITORY_SUITE_DEFINITION)
                .join(model.RepositoryMetadata.table)
                .filter(or_(*trans.app.repository_registry.certified_level_one_clause_list))
                .join(model.User.table)
                .outerjoin(model.RepositoryCategoryAssociation)
                .outerjoin(model.Category.table)
            )
        else:
            # The filter is None.
            return (
                trans.sa_session.query(model.Repository)
                .filter(
                    and_(model.Repository.table.c.deleted == false(), model.Repository.table.c.deprecated == false())
                )
                .join(model.User.table)
                .outerjoin(model.RepositoryCategoryAssociation)
                .outerjoin(model.Category.table)
            )


class DockerImageGrid(RepositoryGrid):
    columns = [
        RepositoryGrid.NameColumn(
            "Name",
            key="name",
            link=(lambda item: dict(operation="view_or_manage_repository", id=item.id)),
            attach_popup=False,
        ),
        RepositoryGrid.DescriptionColumn("Synopsis", key="description", attach_popup=False),
        RepositoryGrid.UserColumn(
            "Owner",
            model_class=model.User,
            link=(lambda item: dict(operation="repositories_by_user", id=item.id)),
            attach_popup=False,
            key="User.username",
        ),
        RepositoryGrid.EmailAlertsColumn("Alert", attach_popup=False),
    ]
    operations = [grids.GridOperation("Include in Docker image", allow_multiple=True)]
    show_item_checkboxes = True


class EmailAlertsRepositoryGrid(RepositoryGrid):
    columns = [
        RepositoryGrid.NameColumn(
            "Name",
            key="name",
            link=(lambda item: dict(operation="view_or_manage_repository", id=item.id)),
            attach_popup=False,
        ),
        RepositoryGrid.DescriptionColumn("Synopsis", key="description", attach_popup=False),
        RepositoryGrid.UserColumn(
            "Owner",
            model_class=model.User,
            link=(lambda item: dict(operation="repositories_by_user", id=item.id)),
            attach_popup=False,
            key="User.username",
        ),
        RepositoryGrid.EmailAlertsColumn("Alert", attach_popup=False),
        # Columns that are valid for filtering but are not visible.
        grids.DeletedColumn("Deleted", key="deleted", visible=False, filterable="advanced"),
    ]
    operations = [grids.GridOperation("Receive email alerts", allow_multiple=True)]
    global_actions = [
        grids.GridAction("User preferences", dict(controller="user", action="index", cntrller="repository"))
    ]


class MatchedRepositoryGrid(grids.Grid):
    # This grid filters out repositories that have been marked as deleted or deprecated.

    class NameColumn(grids.TextColumn):
        def get_value(self, trans, grid, repository_metadata):
            return escape_html(repository_metadata.repository.name)

    class DescriptionColumn(grids.TextColumn):
        def get_value(self, trans, grid, repository_metadata):
            return escape_html(repository_metadata.repository.description)

    class RevisionColumn(grids.TextColumn):
        def get_value(self, trans, grid, repository_metadata):
            return repository_metadata.changeset_revision

    class UserColumn(grids.TextColumn):
        def get_value(self, trans, grid, repository_metadata):
            if repository_metadata.repository.user:
                return escape_html(repository_metadata.repository.user.username)
            return "no user"

    # Grid definition
    title = "Matching repositories"
    model_class = model.RepositoryMetadata
    default_sort_key = "Repository.name"
    use_hide_message = False
    columns = [
        NameColumn(
            "Repository name",
            link=(lambda item: dict(operation="view_or_manage_repository", id=item.id)),
            attach_popup=True,
        ),
        DescriptionColumn("Synopsis", attach_popup=False),
        RevisionColumn("Revision"),
        UserColumn("Owner", model_class=model.User, attach_popup=False),
    ]
    operations = [grids.GridOperation("Install to Galaxy", allow_multiple=True)]
    num_rows_per_page = 50
    use_paging = False

    def build_initial_query(self, trans, **kwd):
        clause_list = []
        if match_tuples := kwd.get("match_tuples", []):
            for match_tuple in match_tuples:
                repository_id, changeset_revision = match_tuple
                clause_list.append(
                    and_(
                        model.RepositoryMetadata.repository_id == int(repository_id),
                        model.RepositoryMetadata.changeset_revision == changeset_revision,
                    )
                )
            return (
                trans.sa_session.query(model.RepositoryMetadata)
                .join(model.Repository)
                .filter(
                    and_(model.Repository.table.c.deleted == false(), model.Repository.table.c.deprecated == false())
                )
                .join(model.User.table)
                .filter(or_(*clause_list))
                .order_by(model.Repository.name)
            )
        # Return an empty query
        return trans.sa_session.query(model.RepositoryMetadata).filter(model.RepositoryMetadata.id < 0)


class InstallMatchedRepositoryGrid(MatchedRepositoryGrid):
    columns = list(MatchedRepositoryGrid.columns)
    # Override the NameColumn
    columns[0] = MatchedRepositoryGrid.NameColumn(
        "Name", link=(lambda item: dict(operation="view_or_manage_repository", id=item.id)), attach_popup=False
    )


class MyWritableRepositoriesGrid(RepositoryGrid):
    # This grid filters out repositories that have been marked as either deprecated or deleted.
    title = "Repositories I can change"
    columns = [
        RepositoryGrid.NameColumn(
            "Name",
            key="name",
            link=(lambda item: dict(operation="view_or_manage_repository", id=item.id)),
            attach_popup=False,
        ),
        RepositoryGrid.TypeColumn("Type"),
        RepositoryGrid.MetadataRevisionColumn("Metadata<br/>Revisions"),
        RepositoryGrid.UserColumn(
            "Owner",
            model_class=model.User,
            link=(lambda item: dict(operation="repositories_by_user", id=item.id)),
            attach_popup=False,
            key="User.username",
        ),
    ]
    columns.append(
        grids.MulticolFilterColumn(
            "Search repository name",
            cols_to_filter=[columns[0]],
            key="free-text-search",
            visible=False,
            filterable="standard",
        )
    )

    def build_initial_query(self, trans, **kwd):
        # TODO: improve performance by adding a db table associating users with repositories for which they have write access.
        username = trans.user.username
        clause_list = []
        for repository in trans.sa_session.query(model.Repository).filter(
            and_(model.Repository.table.c.deprecated == false(), model.Repository.table.c.deleted == false())
        ):
            allow_push = repository.allow_push()
            if allow_push:
                allow_push_usernames = allow_push.split(",")
                if username in allow_push_usernames:
                    clause_list.append(model.Repository.table.c.id == repository.id)
        if clause_list:
            return trans.sa_session.query(model.Repository).filter(or_(*clause_list)).join(model.User.table)
        # Return an empty query.
        return trans.sa_session.query(model.Repository).filter(model.Repository.table.c.id < 0)


class RepositoriesByUserGrid(RepositoryGrid):
    title = "Repositories by user"
    columns = [
        RepositoryGrid.NameColumn(
            "Name",
            key="name",
            link=(lambda item: dict(operation="view_or_manage_repository", id=item.id)),
            attach_popup=False,
        ),
        RepositoryGrid.DescriptionColumn("Synopsis", key="description", attach_popup=False),
        RepositoryGrid.TypeColumn("Type"),
        RepositoryGrid.MetadataRevisionColumn("Metadata<br/>Revisions"),
        RepositoryGrid.CategoryColumn("Category", model_class=model.Category, key="Category.name", attach_popup=False),
    ]
    default_filter = dict(deleted="False")

    def build_initial_query(self, trans, **kwd):
        decoded_user_id = trans.security.decode_id(kwd["user_id"])
        filter = trans.app.repository_grid_filter_manager.get_filter(trans)
        if filter == trans.app.repository_grid_filter_manager.filters.CERTIFIED_LEVEL_ONE:
            return (
                trans.sa_session.query(model.Repository)
                .filter(model.Repository.table.c.user_id == decoded_user_id)
                .join(model.RepositoryMetadata.table)
                .filter(or_(*trans.app.repository_registry.certified_level_one_clause_list))
                .join(model.User.table)
                .outerjoin(model.RepositoryCategoryAssociation)
                .outerjoin(model.Category.table)
            )
        if filter == trans.app.repository_grid_filter_manager.filters.CERTIFIED_LEVEL_ONE_SUITES:
            return (
                trans.sa_session.query(model.Repository)
                .filter(
                    and_(
                        model.Repository.type == rt_util.REPOSITORY_SUITE_DEFINITION,
                        model.Repository.table.c.user_id == decoded_user_id,
                    )
                )
                .join(model.RepositoryMetadata.table)
                .filter(or_(*trans.app.repository_registry.certified_level_one_clause_list))
                .join(model.User.table)
                .outerjoin(model.RepositoryCategoryAssociation)
                .outerjoin(model.Category.table)
            )
        else:
            # The value of filter is None.
            return (
                trans.sa_session.query(model.Repository)
                .filter(
                    and_(
                        model.Repository.table.c.deleted == false(),
                        model.Repository.table.c.deprecated == false(),
                        model.Repository.table.c.user_id == decoded_user_id,
                    )
                )
                .join(model.User.table)
                .outerjoin(model.RepositoryCategoryAssociation)
                .outerjoin(model.Category.table)
            )


class RepositoriesInCategoryGrid(RepositoryGrid):
    title = "Category"

    columns = [
        RepositoryGrid.NameColumn(
            "Name",
            key="name",
            link=(lambda item: dict(controller="repository", operation="view_or_manage_repository", id=item.id)),
            attach_popup=False,
        ),
        RepositoryGrid.DescriptionColumn("Synopsis", key="description", attach_popup=False),
        RepositoryGrid.TypeColumn("Type"),
        RepositoryGrid.MetadataRevisionColumn("Metadata<br/>Revisions"),
        RepositoryGrid.UserColumn(
            "Owner",
            model_class=model.User,
            link=(lambda item: dict(controller="repository", operation="repositories_by_user", id=item.id)),
            attach_popup=False,
            key="User.username",
        ),
        # Columns that are valid for filtering but are not visible.
        RepositoryGrid.EmailColumn("Email", model_class=model.User, key="email", visible=False),
    ]
    columns.append(
        grids.MulticolFilterColumn(
            "Search repository name, description",
            cols_to_filter=[columns[0], columns[1]],
            key="free-text-search",
            visible=False,
            filterable="standard",
        )
    )

    def build_initial_query(self, trans, **kwd):
        category_id = kwd.get("id", None)
        filter = trans.app.repository_grid_filter_manager.get_filter(trans)
        if filter == trans.app.repository_grid_filter_manager.filters.CERTIFIED_LEVEL_ONE:
            if category_id:
                category = suc.get_category(trans.app, category_id)
                if category:
                    return (
                        trans.sa_session.query(model.Repository)
                        .join(model.RepositoryMetadata.table)
                        .filter(or_(*trans.app.repository_registry.certified_level_one_clause_list))
                        .join(model.User.table)
                        .outerjoin(model.RepositoryCategoryAssociation)
                        .outerjoin(model.Category.table)
                        .filter(model.Category.table.c.name == category.name)
                    )
            return (
                trans.sa_session.query(model.Repository)
                .join(model.RepositoryMetadata.table)
                .filter(or_(*trans.app.repository_registry.certified_level_one_clause_list))
                .join(model.User.table)
                .outerjoin(model.RepositoryCategoryAssociation)
                .outerjoin(model.Category.table)
            )
        if filter == trans.app.repository_grid_filter_manager.filters.CERTIFIED_LEVEL_ONE_SUITES:
            if category_id:
                category = suc.get_category(trans.app, category_id)
                if category:
                    return (
                        trans.sa_session.query(model.Repository)
                        .filter(model.Repository.type == rt_util.REPOSITORY_SUITE_DEFINITION)
                        .join(model.RepositoryMetadata.table)
                        .filter(or_(*trans.app.repository_registry.certified_level_one_clause_list))
                        .join(model.User.table)
                        .outerjoin(model.RepositoryCategoryAssociation)
                        .outerjoin(model.Category.table)
                        .filter(model.Category.table.c.name == category.name)
                    )
            return (
                trans.sa_session.query(model.Repository)
                .filter(model.Repository.type == rt_util.REPOSITORY_SUITE_DEFINITION)
                .join(model.RepositoryMetadata.table)
                .filter(or_(*trans.app.repository_registry.certified_level_one_clause_list))
                .join(model.User.table)
                .outerjoin(model.RepositoryCategoryAssociation)
                .outerjoin(model.Category.table)
            )
        else:
            # The value of filter is None.
            if category_id:
                category = suc.get_category(trans.app, category_id)
                if category:
                    return (
                        trans.sa_session.query(model.Repository)
                        .filter(
                            and_(
                                model.Repository.table.c.deleted == false(),
                                model.Repository.table.c.deprecated == false(),
                            )
                        )
                        .join(model.User.table)
                        .outerjoin(model.RepositoryCategoryAssociation)
                        .outerjoin(model.Category.table)
                        .filter(model.Category.table.c.name == category.name)
                    )
            return (
                trans.sa_session.query(model.Repository)
                .filter(
                    and_(model.Repository.table.c.deleted == false(), model.Repository.table.c.deprecated == false())
                )
                .join(model.User.table)
                .outerjoin(model.RepositoryCategoryAssociation)
                .outerjoin(model.Category.table)
            )


class RepositoriesIOwnGrid(RepositoryGrid):
    title = "Repositories I own"
    columns = [
        RepositoryGrid.NameColumn(
            "Name",
            key="name",
            link=(lambda item: dict(operation="view_or_manage_repository", id=item.id)),
            attach_popup=False,
        ),
        RepositoryGrid.TypeColumn("Type"),
        RepositoryGrid.MetadataRevisionColumn("Metadata<br/>Revisions"),
        RepositoryGrid.DeprecatedColumn("Deprecated"),
    ]
    columns.append(
        grids.MulticolFilterColumn(
            "Search repository name",
            cols_to_filter=[columns[0]],
            key="free-text-search",
            visible=False,
            filterable="standard",
        )
    )

    def build_initial_query(self, trans, **kwd):
        return (
            trans.sa_session.query(model.Repository)
            .filter(
                and_(model.Repository.table.c.deleted == false(), model.Repository.table.c.user_id == trans.user.id)
            )
            .join(model.User.table)
            .outerjoin(model.RepositoryCategoryAssociation)
            .outerjoin(model.Category.table)
        )


class RepositoriesICanAdministerGrid(RepositoryGrid):
    title = "Repositories I can administer"
    columns = [
        RepositoryGrid.NameColumn(
            "Name",
            key="name",
            link=(lambda item: dict(operation="view_or_manage_repository", id=item.id)),
            attach_popup=False,
        ),
        RepositoryGrid.UserColumn("Owner"),
        RepositoryGrid.MetadataRevisionColumn("Metadata<br/>Revisions"),
        RepositoryGrid.DeprecatedColumn("Deprecated"),
    ]
    columns.append(
        grids.MulticolFilterColumn(
            "Search repository name",
            cols_to_filter=[columns[0]],
            key="free-text-search",
            visible=False,
            filterable="standard",
        )
    )

    def build_initial_query(self, trans, **kwd):
        """
        Retrieve all repositories for which the current user has been granted administrative privileges.
        """
        current_user = trans.user
        # Build up an or-based clause list containing role table records.
        clause_list = []
        # Include each of the user's roles.
        for ura in current_user.roles:
            clause_list.append(model.Role.table.c.id == ura.role_id)
        # Include each role associated with each group of which the user is a member.
        for uga in current_user.groups:
            group = uga.group
            for gra in group.roles:
                clause_list.append(model.Role.table.c.id == gra.role_id)
        # Filter out repositories for which the user does not have the administrative role either directly
        # via a role association or indirectly via a group -> role association.
        return (
            trans.sa_session.query(model.Repository)
            .filter(model.Repository.table.c.deleted == false())
            .outerjoin(model.RepositoryRoleAssociation)
            .outerjoin(model.Role.table)
            .filter(or_(*clause_list))
            .join(model.User.table)
            .outerjoin(model.RepositoryCategoryAssociation)
            .outerjoin(model.Category.table)
        )


class RepositoriesMissingToolTestComponentsGrid(RepositoryGrid):
    # This grid displays only the latest installable revision of each repository.
    title = "Repositories with missing tool test components"
    columns = [
        RepositoryGrid.NameColumn(
            "Name",
            key="name",
            link=(lambda item: dict(operation="view_or_manage_repository", id=item.id)),
            attach_popup=False,
        ),
        RepositoryGrid.LatestInstallableRevisionColumn("Latest Installable Revision"),
        RepositoryGrid.UserColumn(
            "Owner",
            key="User.username",
            model_class=model.User,
            link=(lambda item: dict(operation="repositories_by_user", id=item.id)),
            attach_popup=False,
        ),
    ]
    columns.append(
        grids.MulticolFilterColumn(
            "Search repository name",
            cols_to_filter=[columns[0]],
            key="free-text-search",
            visible=False,
            filterable="standard",
        )
    )

    def build_initial_query(self, trans, **kwd):
        # Filter by latest installable revisions that contain tools with missing tool test components.
        revision_clause_list = []
        for repository in trans.sa_session.query(model.Repository).filter(
            and_(model.Repository.table.c.deprecated == false(), model.Repository.table.c.deleted == false())
        ):
            changeset_revision = (
                grids_util.filter_by_latest_downloadable_changeset_revision_that_has_missing_tool_test_components(
                    trans, repository
                )
            )
            if changeset_revision:
                revision_clause_list.append(model.RepositoryMetadata.table.c.changeset_revision == changeset_revision)
        if revision_clause_list:
            return (
                trans.sa_session.query(model.Repository)
                .filter(
                    and_(model.Repository.table.c.deprecated == false(), model.Repository.table.c.deleted == false())
                )
                .join(model.RepositoryMetadata)
                .filter(or_(*revision_clause_list))
                .join(model.User.table)
            )
        # Return an empty query.
        return trans.sa_session.query(model.Repository).filter(model.Repository.table.c.id < 0)


class MyWritableRepositoriesMissingToolTestComponentsGrid(RepositoriesMissingToolTestComponentsGrid):
    # This grid displays only the latest installable revision of each repository.
    title = "Repositories I can change with missing tool test components"
    columns = list(RepositoriesMissingToolTestComponentsGrid.columns)

    def build_initial_query(self, trans, **kwd):
        # First get all repositories that the current user is authorized to update.
        username = trans.user.username
        user_clause_list = []
        for repository in trans.sa_session.query(model.Repository).filter(
            and_(model.Repository.table.c.deprecated == false(), model.Repository.table.c.deleted == false())
        ):
            allow_push = repository.allow_push()
            if allow_push:
                allow_push_usernames = allow_push.split(",")
                if username in allow_push_usernames:
                    user_clause_list.append(model.Repository.table.c.id == repository.id)
        if user_clause_list:
            # We have the list of repositories that the current user is authorized to update, so filter
            # further by latest installable revisions that contain tools with missing tool test components.
            revision_clause_list = []
            for repository in (
                trans.sa_session.query(model.Repository)
                .filter(
                    and_(model.Repository.table.c.deprecated == false(), model.Repository.table.c.deleted == false())
                )
                .filter(or_(*user_clause_list))
            ):
                changeset_revision = (
                    grids_util.filter_by_latest_downloadable_changeset_revision_that_has_missing_tool_test_components(
                        trans, repository
                    )
                )
                if changeset_revision:
                    revision_clause_list.append(
                        model.RepositoryMetadata.table.c.changeset_revision == changeset_revision
                    )
            if revision_clause_list:
                return (
                    trans.sa_session.query(model.Repository)
                    .filter(
                        and_(
                            model.Repository.table.c.deprecated == false(), model.Repository.table.c.deleted == false()
                        )
                    )
                    .join(model.User.table)
                    .filter(or_(*user_clause_list))
                    .join(model.RepositoryMetadata)
                    .filter(or_(*revision_clause_list))
                )
        # Return an empty query.
        return trans.sa_session.query(model.Repository).filter(model.Repository.table.c.id < 0)


class DeprecatedRepositoriesIOwnGrid(RepositoriesIOwnGrid):
    title = "Deprecated repositories I own"
    columns = [
        RepositoriesIOwnGrid.NameColumn(
            "Name",
            key="name",
            link=(lambda item: dict(operation="view_or_manage_repository", id=item.id)),
            attach_popup=False,
        ),
        RepositoryGrid.TypeColumn("Type"),
        RepositoriesIOwnGrid.MetadataRevisionColumn("Metadata<br/>Revisions"),
        RepositoriesIOwnGrid.CategoryColumn(
            "Category", model_class=model.Category, key="Category.name", attach_popup=False
        ),
    ]
    columns.append(
        grids.MulticolFilterColumn(
            "Search repository name",
            cols_to_filter=[columns[0]],
            key="free-text-search",
            visible=False,
            filterable="standard",
        )
    )

    def build_initial_query(self, trans, **kwd):
        return (
            trans.sa_session.query(model.Repository)
            .filter(
                and_(
                    model.Repository.table.c.deleted == false(),
                    model.Repository.table.c.user_id == trans.user.id,
                    model.Repository.table.c.deprecated == true(),
                )
            )
            .join(model.User.table)
            .outerjoin(model.RepositoryCategoryAssociation)
            .outerjoin(model.Category.table)
        )


class RepositoriesWithInvalidToolsGrid(RepositoryGrid):
    # This grid displays only the latest installable revision of each repository.

    class InvalidToolConfigColumn(grids.GridColumn):
        def __init__(self, col_name):
            grids.GridColumn.__init__(self, col_name)

        def get_value(self, trans, grid, repository):
            # At the time this grid is displayed we know that the received repository will have invalid tools in its latest changeset revision
            # that has associated metadata.
            val = ""
            repository_metadata = grids_util.get_latest_repository_metadata_if_it_includes_invalid_tools(
                trans, repository
            )
            metadata = repository_metadata.metadata
            if invalid_tools := metadata.get("invalid_tools", []):
                for invalid_tool_config in invalid_tools:
                    href_str = f'<a href="load_invalid_tool?repository_id={trans.security.encode_id(repository.id)}&tool_config={invalid_tool_config}&changeset_revision={repository_metadata.changeset_revision}">{invalid_tool_config}</a>'
                    val += href_str
                    val += "<br/>"
                val = val.rstrip("<br/>")
            return val

    title = "Repositories with invalid tools"
    columns = [
        InvalidToolConfigColumn("Tool config"),
        RepositoryGrid.NameColumn(
            "Name",
            key="name",
            link=(lambda item: dict(operation="view_or_manage_repository", id=item.id)),
            attach_popup=False,
        ),
        RepositoryGrid.LatestInstallableRevisionColumn("Latest Metadata Revision"),
        RepositoryGrid.UserColumn(
            "Owner",
            key="User.username",
            model_class=model.User,
            link=(lambda item: dict(operation="repositories_by_user", id=item.id)),
            attach_popup=False,
        ),
    ]

    def build_initial_query(self, trans, **kwd):
        # Filter by latest metadata revisions that contain invalid tools.
        revision_clause_list = []
        for repository in trans.sa_session.query(model.Repository).filter(
            and_(model.Repository.table.c.deprecated == false(), model.Repository.table.c.deleted == false())
        ):
            changeset_revision = grids_util.filter_by_latest_metadata_changeset_revision_that_has_invalid_tools(
                trans, repository
            )
            if changeset_revision:
                revision_clause_list.append(model.RepositoryMetadata.table.c.changeset_revision == changeset_revision)
        if revision_clause_list:
            return (
                trans.sa_session.query(model.Repository)
                .filter(
                    and_(model.Repository.table.c.deprecated == false(), model.Repository.table.c.deleted == false())
                )
                .join(model.RepositoryMetadata)
                .filter(or_(*revision_clause_list))
                .join(model.User.table)
            )
        # Return an empty query.
        return trans.sa_session.query(model.Repository).filter(model.Repository.table.c.id < 0)


class MyWritableRepositoriesWithInvalidToolsGrid(RepositoriesWithInvalidToolsGrid):
    # This grid displays only the latest installable revision of each repository.
    title = "Repositories I can change with invalid tools"
    columns = list(RepositoriesWithInvalidToolsGrid.columns)

    def build_initial_query(self, trans, **kwd):
        # First get all repositories that the current user is authorized to update.
        username = trans.user.username
        user_clause_list = []
        for repository in trans.sa_session.query(model.Repository).filter(
            and_(model.Repository.table.c.deprecated == false(), model.Repository.table.c.deleted == false())
        ):
            allow_push = repository.allow_push()
            if allow_push:
                allow_push_usernames = allow_push.split(",")
                if username in allow_push_usernames:
                    user_clause_list.append(model.Repository.table.c.id == repository.id)
        if user_clause_list:
            # We have the list of repositories that the current user is authorized to update, so filter
            # further by latest metadata revisions that contain invalid tools.
            revision_clause_list = []
            for repository in (
                trans.sa_session.query(model.Repository)
                .filter(
                    and_(model.Repository.table.c.deprecated == false(), model.Repository.table.c.deleted == false())
                )
                .filter(or_(*user_clause_list))
            ):
                changeset_revision = grids_util.filter_by_latest_metadata_changeset_revision_that_has_invalid_tools(
                    trans, repository
                )
                if changeset_revision:
                    revision_clause_list.append(
                        model.RepositoryMetadata.table.c.changeset_revision == changeset_revision
                    )
            if revision_clause_list:
                return (
                    trans.sa_session.query(model.Repository)
                    .filter(
                        and_(
                            model.Repository.table.c.deprecated == false(), model.Repository.table.c.deleted == false()
                        )
                    )
                    .join(model.User.table)
                    .filter(or_(*user_clause_list))
                    .join(model.RepositoryMetadata)
                    .filter(or_(*revision_clause_list))
                )
        # Return an empty query.
        return trans.sa_session.query(model.Repository).filter(model.Repository.table.c.id < 0)


class RepositoryMetadataGrid(grids.Grid):
    class RepositoryNameColumn(grids.TextColumn):
        def get_value(self, trans, grid, repository_metadata):
            repository = repository_metadata.repository
            return escape_html(repository.name)

    class RepositoryTypeColumn(grids.TextColumn):
        def get_value(self, trans, grid, repository_metadata):
            repository = repository_metadata.repository
            type_class = repository.get_type_class(trans.app)
            return escape_html(type_class.label)

    class RepositoryOwnerColumn(grids.TextColumn):
        def get_value(self, trans, grid, repository_metadata):
            repository = repository_metadata.repository
            return escape_html(repository.user.username)

    class ChangesetRevisionColumn(grids.TextColumn):
        def get_value(self, trans, grid, repository_metadata):
            repository = repository_metadata.repository
            changeset_revision = repository_metadata.changeset_revision
            changeset_revision_label = hg_util.get_revision_label(
                trans.app, repository, changeset_revision, include_date=True
            )
            return changeset_revision_label

    class MaliciousColumn(grids.BooleanColumn):
        def get_value(self, trans, grid, repository_metadata):
            if repository_metadata.malicious:
                return "yes"
            return ""

    class DownloadableColumn(grids.BooleanColumn):
        def get_value(self, trans, grid, repository_metadata):
            if repository_metadata.downloadable:
                return "yes"
            return ""

    class HasRepositoryDependenciesColumn(grids.BooleanColumn):
        def get_value(self, trans, grid, repository_metadata):
            if repository_metadata.has_repository_dependencies:
                return "yes"
            return ""

    class IncludesDatatypesColumn(grids.BooleanColumn):
        def get_value(self, trans, grid, repository_metadata):
            if repository_metadata.includes_datatypes:
                return "yes"
            return ""

    class IncludesToolsColumn(grids.BooleanColumn):
        def get_value(self, trans, grid, repository_metadata):
            if repository_metadata.includes_tools:
                return "yes"
            return ""

    class IncludesToolDependenciesColumn(grids.BooleanColumn):
        def get_value(self, trans, grid, repository_metadata):
            if repository_metadata.includes_tool_dependencies:
                return "yes"
            return ""

    class IncludesWorkflowsColumn(grids.BooleanColumn):
        def get_value(self, trans, grid, repository_metadata):
            if repository_metadata.includes_workflows:
                return "yes"
            return ""

    title = "Repository metadata"
    model_class = model.RepositoryMetadata
    default_sort_key = "Repository.name"
    columns = [
        RepositoryNameColumn(
            "Repository name",
            key="Repository.name",
            link=(lambda item: dict(operation="view_or_manage_repository", id=item.id)),
            attach_popup=False,
        ),
        RepositoryNameColumn("Type"),
        RepositoryOwnerColumn("Owner", model_class=model.User, attach_popup=False, key="User.username"),
    ]
    columns.append(
        grids.MulticolFilterColumn(
            "Search repository name, description",
            cols_to_filter=[columns[0], columns[1]],
            key="free-text-search",
            visible=False,
            filterable="standard",
        )
    )
    default_filter = dict(malicious="False")
    num_rows_per_page = 50
    use_paging = True
    allow_fetching_all_results = False

    def build_initial_query(self, trans, **kwd):
        return (
            trans.sa_session.query(model.RepositoryMetadata)
            .join(model.Repository)
            .filter(and_(model.Repository.table.c.deleted == false(), model.Repository.table.c.deprecated == false()))
            .join(model.User.table)
        )


class RepositoryDependenciesGrid(RepositoryMetadataGrid):
    class RequiredRepositoryColumn(grids.TextColumn):
        def get_value(self, trans, grid, repository_metadata):
            rd_str = []
            if repository_metadata:
                metadata = repository_metadata.metadata
                if metadata:
                    rd_dict = metadata.get("repository_dependencies", {})
                    if rd_dict:
                        rd_tups = rd_dict["repository_dependencies"]
                        # "repository_dependencies": [["http://localhost:9009", "bwa059", "test", "a07baa797d53"]]
                        # Sort rd_tups by by required repository name.
                        sorted_rd_tups = sorted(rd_tups, key=lambda rd_tup: rd_tup[1])
                        for rd_tup in sorted_rd_tups:
                            name, owner, changeset_revision = rd_tup[1:4]
                            rd_line = ""
                            required_repository = repository_util.get_repository_by_name_and_owner(
                                trans.app, name, owner
                            )
                            if required_repository and not required_repository.deleted:
                                required_repository_id = trans.security.encode_id(required_repository.id)
                                required_repository_metadata = (
                                    metadata_util.get_repository_metadata_by_repository_id_changeset_revision(
                                        trans.app, required_repository_id, changeset_revision
                                    )
                                )
                                if not required_repository_metadata:
                                    updated_changeset_revision = metadata_util.get_next_downloadable_changeset_revision(
                                        trans.app, required_repository, changeset_revision
                                    )
                                    required_repository_metadata = (
                                        metadata_util.get_repository_metadata_by_repository_id_changeset_revision(
                                            trans.app, required_repository_id, updated_changeset_revision
                                        )
                                    )
                                required_repository_metadata_id = trans.security.encode_id(
                                    required_repository_metadata.id
                                )
                                rd_line += f'<a href="browse_repository_dependencies?operation=view_or_manage_repository&id={required_repository_metadata_id}">'
                            rd_line += f"Repository <b>{escape_html(name)}</b> revision <b>{escape_html(owner)}</b> owned by <b>{escape_html(changeset_revision)}</b>"
                            if required_repository:
                                rd_line += "</a>"
                            rd_str.append(rd_line)
            return "<br />".join(rd_str)

    title = "Valid repository dependency definitions in this tool shed"
    default_sort_key = "Repository.name"
    columns = [
        RequiredRepositoryColumn("Repository dependency", attach_popup=False),
        RepositoryMetadataGrid.RepositoryNameColumn(
            "Repository name",
            model_class=model.Repository,
            link=(lambda item: dict(operation="view_or_manage_repository", id=item.id)),
            attach_popup=False,
            key="Repository.name",
        ),
        RepositoryMetadataGrid.RepositoryOwnerColumn(
            "Owner", model_class=model.User, attach_popup=False, key="User.username"
        ),
        RepositoryMetadataGrid.ChangesetRevisionColumn("Revision", attach_popup=False),
    ]
    columns.append(
        grids.MulticolFilterColumn(
            "Search repository name, owner",
            cols_to_filter=[columns[1], columns[2]],
            key="free-text-search",
            visible=False,
            filterable="standard",
        )
    )

    def build_initial_query(self, trans, **kwd):
        return (
            trans.sa_session.query(model.RepositoryMetadata)
            .join(model.Repository)
            .filter(
                and_(
                    model.RepositoryMetadata.table.c.has_repository_dependencies == true(),
                    model.Repository.table.c.deleted == false(),
                    model.Repository.table.c.deprecated == false(),
                )
            )
            .join(model.User.table)
        )


class DatatypesGrid(RepositoryMetadataGrid):
    class DatatypesColumn(grids.TextColumn):
        def get_value(self, trans, grid, repository_metadata):
            datatype_list = []
            if repository_metadata:
                metadata = repository_metadata.metadata
                if metadata:
                    datatype_dicts = metadata.get("datatypes", [])
                    if datatype_dicts:
                        # Create tuples of the attributes we want so we can sort them by extension.
                        datatype_tups = []
                        for datatype_dict in datatype_dicts:
                            # Example: {"display_in_upload": "true", "dtype": "galaxy.datatypes.blast:BlastXml", "extension": "blastxml", "mimetype": "application/xml"}
                            extension = datatype_dict.get("extension", "")
                            dtype = datatype_dict.get("dtype", "")
                            # For now we'll just display extension and dtype.
                            if extension and dtype:
                                datatype_tups.append((extension, dtype))
                        sorted_datatype_tups = sorted(datatype_tups, key=lambda datatype_tup: datatype_tup[0])
                        for datatype_tup in sorted_datatype_tups:
                            extension, datatype = datatype_tup[:2]
                            datatype_str = f'<a href="browse_datatypes?operation=view_or_manage_repository&id={trans.security.encode_id(repository_metadata.id)}">'
                            datatype_str += f"<b>{escape_html(extension)}:</b> {escape_html(datatype)}"
                            datatype_str += "</a>"
                            datatype_list.append(datatype_str)
            return "<br />".join(datatype_list)

    title = "Custom datatypes in this tool shed"
    default_sort_key = "Repository.name"
    columns = [
        DatatypesColumn("Datatype extension and class", attach_popup=False),
        RepositoryMetadataGrid.RepositoryNameColumn(
            "Repository name",
            model_class=model.Repository,
            link=(lambda item: dict(operation="view_or_manage_repository", id=item.id)),
            attach_popup=False,
            key="Repository.name",
        ),
        RepositoryMetadataGrid.RepositoryOwnerColumn(
            "Owner", model_class=model.User, attach_popup=False, key="User.username"
        ),
        RepositoryMetadataGrid.ChangesetRevisionColumn("Revision", attach_popup=False),
    ]
    columns.append(
        grids.MulticolFilterColumn(
            "Search repository name, owner",
            cols_to_filter=[columns[1], columns[2]],
            key="free-text-search",
            visible=False,
            filterable="standard",
        )
    )

    def build_initial_query(self, trans, **kwd):
        return (
            trans.sa_session.query(model.RepositoryMetadata)
            .join(model.Repository)
            .filter(
                and_(
                    model.RepositoryMetadata.table.c.includes_datatypes == true(),
                    model.Repository.table.c.deleted == false(),
                    model.Repository.table.c.deprecated == false(),
                )
            )
            .join(model.User.table)
        )


class ToolDependenciesGrid(RepositoryMetadataGrid):
    class ToolDependencyColumn(grids.TextColumn):
        def get_value(self, trans, grid, repository_metadata):
            td_str = ""
            if repository_metadata:
                metadata = repository_metadata.metadata
                if metadata:
                    tds_dict = metadata.get("tool_dependencies", {})
                    if tds_dict:
                        # Example: {"bwa/0.5.9": {"name": "bwa", "type": "package", "version": "0.5.9"}}
                        sorted_keys = sorted(tds_dict.keys())
                        num_keys = len(sorted_keys)
                        # Handle environment settings first.
                        if "set_environment" in sorted_keys:
                            # Example: "set_environment": [{"name": "JAVA_JAR_FILE", "type": "set_environment"}]
                            env_dicts = tds_dict["set_environment"]
                            num_env_dicts = len(env_dicts)
                            if num_env_dicts > 0:
                                td_str += f'<a href="browse_datatypes?operation=view_or_manage_repository&id={trans.security.encode_id(repository_metadata.id)}">'
                                td_str += "<b>environment:</b> "
                                td_str += ", ".join(escape_html(env_dict["name"]) for env_dict in env_dicts)
                                td_str += "</a><br/>"
                        for index, key in enumerate(sorted_keys):
                            if key == "set_environment":
                                continue
                            td_dict = tds_dict[key]
                            # Example: {"name": "bwa", "type": "package", "version": "0.5.9"}
                            name = td_dict["name"]
                            version = td_dict["version"]
                            td_str += f'<a href="browse_datatypes?operation=view_or_manage_repository&id={trans.security.encode_id(repository_metadata.id)}">'
                            td_str += f"<b>{escape_html(name)}</b> version <b>{escape_html(version)}</b>"
                            td_str += "</a>"
                            if index < num_keys - 1:
                                td_str += "<br/>"
            return td_str

    title = "Tool dependency definitions in this tool shed"
    default_sort_key = "Repository.name"
    columns = [
        ToolDependencyColumn("Tool dependency", attach_popup=False),
        RepositoryMetadataGrid.RepositoryNameColumn(
            "Repository name",
            model_class=model.Repository,
            link=(lambda item: dict(operation="view_or_manage_repository", id=item.id)),
            attach_popup=False,
            key="Repository.name",
        ),
        RepositoryMetadataGrid.RepositoryOwnerColumn(
            "Owner", model_class=model.User, attach_popup=False, key="User.username"
        ),
        RepositoryMetadataGrid.ChangesetRevisionColumn("Revision", attach_popup=False),
    ]
    columns.append(
        grids.MulticolFilterColumn(
            "Search repository name, owner",
            cols_to_filter=[columns[1], columns[2]],
            key="free-text-search",
            visible=False,
            filterable="standard",
        )
    )

    def build_initial_query(self, trans, **kwd):
        return (
            trans.sa_session.query(model.RepositoryMetadata)
            .join(model.Repository)
            .filter(
                and_(
                    model.RepositoryMetadata.table.c.includes_tool_dependencies == true(),
                    model.Repository.table.c.deleted == false(),
                    model.Repository.table.c.deprecated == false(),
                )
            )
            .join(model.User.table)
        )


class ToolsGrid(RepositoryMetadataGrid):
    class ToolsColumn(grids.TextColumn):
        def get_value(self, trans, grid, repository_metadata):
            tool_line = []
            if repository_metadata:
                metadata = repository_metadata.metadata
                if metadata:
                    tool_dicts = metadata.get("tools", [])
                    if tool_dicts:
                        # Create tuples of the attributes we want so we can sort them by extension.
                        tool_tups = []
                        for tool_dict in tool_dicts:
                            tool_id = tool_dict.get("id", "")
                            version = tool_dict.get("version", "")
                            # For now we'll just display tool id and version.
                            if tool_id and version:
                                tool_tups.append((tool_id, version))
                        sorted_tool_tups = sorted(tool_tups, key=lambda tool_tup: tool_tup[0])
                        for tool_tup in sorted_tool_tups:
                            tool_id, version = tool_tup[:2]
                            tool_str = f'<a href="browse_datatypes?operation=view_or_manage_repository&id={trans.security.encode_id(repository_metadata.id)}">'
                            tool_str += f"<b>{escape_html(tool_id)}:</b> {escape_html(version)}"
                            tool_str += "</a>"
                            tool_line.append(tool_str)
            return "<br />".join(tool_line)

    title = "Valid tools in this tool shed"
    default_sort_key = "Repository.name"
    columns = [
        ToolsColumn("Tool id and version", attach_popup=False),
        RepositoryMetadataGrid.RepositoryNameColumn(
            "Repository name",
            model_class=model.Repository,
            link=(lambda item: dict(operation="view_or_manage_repository", id=item.id)),
            attach_popup=False,
            key="Repository.name",
        ),
        RepositoryMetadataGrid.RepositoryOwnerColumn(
            "Owner", model_class=model.User, attach_popup=False, key="User.username"
        ),
        RepositoryMetadataGrid.ChangesetRevisionColumn("Revision", attach_popup=False),
    ]
    columns.append(
        grids.MulticolFilterColumn(
            "Search repository name, owner",
            cols_to_filter=[columns[1], columns[2]],
            key="free-text-search",
            visible=False,
            filterable="standard",
        )
    )

    def build_initial_query(self, trans, **kwd):
        return (
            trans.sa_session.query(model.RepositoryMetadata)
            .join(model.Repository)
            .filter(
                and_(
                    model.RepositoryMetadata.table.c.includes_tools == true(),
                    model.Repository.table.c.deleted == false(),
                    model.Repository.table.c.deprecated == false(),
                )
            )
            .join(model.User.table)
        )


class ValidCategoryGrid(CategoryGrid):
    class RepositoriesColumn(grids.TextColumn):
        def get_value(self, trans, grid, category):
            category_name = str(category.name)
            filter = trans.app.repository_grid_filter_manager.get_filter(trans)
            if filter == trans.app.repository_grid_filter_manager.filters.CERTIFIED_LEVEL_ONE:
                return (
                    trans.app.repository_registry.certified_level_one_viewable_repositories_and_suites_by_category.get(
                        category_name, 0
                    )
                )
            elif filter == trans.app.repository_grid_filter_manager.filters.CERTIFIED_LEVEL_ONE_SUITES:
                return trans.app.repository_registry.certified_level_one_viewable_suites_by_category.get(
                    category_name, 0
                )
            elif filter == trans.app.repository_grid_filter_manager.filters.SUITES:
                return trans.app.repository_registry.viewable_valid_suites_by_category.get(category_name, 0)
            else:
                # The value filter is None.
                return trans.app.repository_registry.viewable_valid_repositories_and_suites_by_category.get(
                    category_name, 0
                )

    title = "Categories of Valid Repositories"
    model_class = model.Category
    template = "/webapps/tool_shed/category/valid_grid.mako"
    default_sort_key = "name"
    columns = [
        CategoryGrid.NameColumn(
            "Name",
            key="Category.name",
            link=(lambda item: dict(operation="valid_repositories_by_category", id=item.id)),
            attach_popup=False,
        ),
        CategoryGrid.DescriptionColumn("Description", key="Category.description", attach_popup=False),
        # Columns that are valid for filtering but are not visible.
        RepositoriesColumn("Valid repositories", model_class=model.Repository, attach_popup=False),
    ]
    # Override these
    num_rows_per_page = 50


class ValidRepositoryGrid(RepositoryGrid):
    # This grid filters out repositories that have been marked as either deleted or deprecated.

    class CategoryColumn(grids.TextColumn):
        def get_value(self, trans, grid, repository):
            rval = "<ul>"
            if repository.categories:
                for rca in repository.categories:
                    rval += f'<li><a href="browse_repositories?operation=valid_repositories_by_category&id={trans.security.encode_id(rca.category.id)}">{rca.category.name}</a></li>'
            else:
                rval += "<li>not set</li>"
            rval += "</ul>"
            return rval

    class RepositoryCategoryColumn(grids.GridColumn):
        def filter(self, trans, user, query, column_filter):
            """Modify query to filter by category."""
            if column_filter == "All":
                return query
            return query.filter(model.Category.name == column_filter)

    class InstallableRevisionColumn(grids.GridColumn):
        def __init__(self, col_name):
            grids.GridColumn.__init__(self, col_name)

        def get_value(self, trans, grid, repository):
            """Display a SelectField whose options are the changeset_revision strings of all download-able revisions of this repository."""
            select_field = grids_util.build_changeset_revision_select_field(trans, repository, downloadable=True)
            if len(select_field.options) > 1:
                tmpl = f"<select name='{select_field.name}'>"
                for o in select_field.options:
                    tmpl += f"<option value='{o[1]}'>{o[0]}</option>"
                tmpl += "</select>"
                return tmpl
            elif len(select_field.options) == 1:
                return select_field.options[0][0]
            return ""

    title = "Valid Repositories"
    columns = [
        RepositoryGrid.NameColumn("Name", key="name", attach_popup=True),
        RepositoryGrid.DescriptionColumn("Synopsis", key="description", attach_popup=False),
        RepositoryGrid.TypeColumn("Type"),
        InstallableRevisionColumn("Installable Revisions"),
        RepositoryGrid.UserColumn("Owner", model_class=model.User, attach_popup=False),
        # Columns that are valid for filtering but are not visible.
        RepositoryCategoryColumn("Category", model_class=model.Category, key="Category.name", visible=False),
    ]
    columns.append(
        grids.MulticolFilterColumn(
            "Search repository name, description",
            cols_to_filter=[columns[0], columns[1]],
            key="free-text-search",
            visible=False,
            filterable="standard",
        )
    )

    def build_initial_query(self, trans, **kwd):
        filter = trans.app.repository_grid_filter_manager.get_filter(trans)
        if "id" in kwd:
            # The user is browsing categories of valid repositories, so filter the request by the received id,
            # which is a category id.
            if filter == trans.app.repository_grid_filter_manager.filters.CERTIFIED_LEVEL_ONE:
                return (
                    trans.sa_session.query(model.Repository)
                    .join(model.RepositoryMetadata.table)
                    .filter(or_(*trans.app.repository_registry.certified_level_one_clause_list))
                    .join(model.User.table)
                    .join(model.RepositoryCategoryAssociation)
                    .join(model.Category.table)
                    .filter(
                        and_(
                            model.Category.__table__.c.id == trans.security.decode_id(kwd["id"]),
                            model.RepositoryMetadata.table.c.downloadable == true(),
                        )
                    )
                )
            if filter == trans.app.repository_grid_filter_manager.filters.CERTIFIED_LEVEL_ONE_SUITES:
                return (
                    trans.sa_session.query(model.Repository)
                    .filter(model.Repository.type == rt_util.REPOSITORY_SUITE_DEFINITION)
                    .join(model.RepositoryMetadata.table)
                    .filter(or_(*trans.app.repository_registry.certified_level_one_clause_list))
                    .join(model.User.table)
                    .join(model.RepositoryCategoryAssociation)
                    .join(model.Category.table)
                    .filter(
                        and_(
                            model.Category.table.c.id == trans.security.decode_id(kwd["id"]),
                            model.RepositoryMetadata.table.c.downloadable == true(),
                        )
                    )
                )
            else:
                # The value of filter is None.
                return (
                    trans.sa_session.query(model.Repository)
                    .filter(
                        and_(
                            model.Repository.table.c.deleted == false(), model.Repository.table.c.deprecated == false()
                        )
                    )
                    .join(model.RepositoryMetadata.table)
                    .join(model.User.table)
                    .join(model.RepositoryCategoryAssociation)
                    .join(model.Category.table)
                    .filter(
                        and_(
                            model.Category.table.c.id == trans.security.decode_id(kwd["id"]),
                            model.RepositoryMetadata.table.c.downloadable == true(),
                        )
                    )
                )
        # The user performed a free text search on the ValidCategoryGrid.
        if filter == trans.app.repository_grid_filter_manager.filters.CERTIFIED_LEVEL_ONE:
            return (
                trans.sa_session.query(model.Repository)
                .join(model.RepositoryMetadata.table)
                .filter(or_(*trans.app.repository_registry.certified_level_one_clause_list))
                .join(model.User.table)
                .outerjoin(model.RepositoryCategoryAssociation)
                .outerjoin(model.Category.table)
                .filter(model.RepositoryMetadata.table.c.downloadable == true())
            )
        if filter == trans.app.repository_grid_filter_manager.filters.CERTIFIED_LEVEL_ONE_SUITES:
            return (
                trans.sa_session.query(model.Repository)
                .filter(model.Repository.type == rt_util.REPOSITORY_SUITE_DEFINITION)
                .join(model.RepositoryMetadata.table)
                .filter(or_(*trans.app.repository_registry.certified_level_one_clause_list))
                .join(model.User.table)
                .outerjoin(model.RepositoryCategoryAssociation)
                .outerjoin(model.Category.table)
                .filter(model.RepositoryMetadata.table.c.downloadable == true())
            )
        else:
            # The value of filter is None.
            return (
                trans.sa_session.query(model.Repository)
                .filter(
                    and_(model.Repository.table.c.deleted == false(), model.Repository.table.c.deprecated == false())
                )
                .join(model.RepositoryMetadata.table)
                .join(model.User.table)
                .outerjoin(model.RepositoryCategoryAssociation)
                .outerjoin(model.Category.table)
                .filter(model.RepositoryMetadata.table.c.downloadable == true())
            )
