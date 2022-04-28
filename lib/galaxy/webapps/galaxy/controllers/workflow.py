import base64
import json
import logging
from html.parser import HTMLParser
from http.client import HTTPConnection

from markupsafe import escape
from sqlalchemy import (
    and_,
    desc,
)
from sqlalchemy.orm import (
    joinedload,
    lazyload,
    undefer,
)
from sqlalchemy.sql import expression

from galaxy import (
    model,
    util,
    web,
)
from galaxy.managers.sharable import SlugBuilder
from galaxy.managers.workflows import (
    MissingToolsException,
    WorkflowUpdateOptions,
)
from galaxy.model.item_attrs import UsesItemRatings
from galaxy.tools.parameters.basic import workflow_building_modes
from galaxy.util import (
    FILENAME_VALID_CHARS,
    unicodify,
)
from galaxy.util.sanitize_html import sanitize_html
from galaxy.web import (
    error,
    url_for,
)
from galaxy.web.framework.helpers import (
    grids,
    time_ago,
)
from galaxy.webapps.base.controller import (
    BaseUIController,
    SharableMixin,
    UsesStoredWorkflowMixin,
)
from galaxy.workflow.extract import (
    extract_workflow,
    summarize,
)
from galaxy.workflow.modules import (
    load_module_sections,
    module_factory,
)
from galaxy.workflow.render import (
    STANDALONE_SVG_TEMPLATE,
    WorkflowCanvas,
)

log = logging.getLogger(__name__)


class StoredWorkflowListGrid(grids.Grid):
    class StepsColumn(grids.GridColumn):
        def get_value(self, trans, grid, workflow):
            return len(workflow.latest_workflow.steps)

    # Grid definition
    use_panels = True
    title = "Saved Workflows"
    model_class = model.StoredWorkflow
    default_filter = {"name": "All", "tags": "All"}
    default_sort_key = "-update_time"
    columns = [
        grids.TextColumn("Name", key="name", attach_popup=True, filterable="advanced"),
        grids.IndividualTagsColumn(
            "Tags",
            "tags",
            model_tag_association_class=model.StoredWorkflowTagAssociation,
            filterable="advanced",
            grid_name="StoredWorkflowListGrid",
        ),
        StepsColumn("Steps"),
        grids.GridColumn("Created", key="create_time", format=time_ago),
        grids.GridColumn("Last Updated", key="update_time", format=time_ago),
    ]
    columns.append(
        grids.MulticolFilterColumn(
            "Search",
            cols_to_filter=[columns[0], columns[1]],
            key="free-text-search",
            visible=False,
            filterable="standard",
        )
    )
    operations = [
        grids.GridOperation(
            "Edit", allow_multiple=False, condition=(lambda item: not item.deleted), async_compatible=False
        ),
        grids.GridOperation("Run", condition=(lambda item: not item.deleted), async_compatible=False),
        grids.GridOperation("Copy", condition=(lambda item: not item.deleted), async_compatible=False),
        grids.GridOperation("Rename", condition=(lambda item: not item.deleted), async_compatible=False),
        grids.GridOperation("Sharing", condition=(lambda item: not item.deleted), async_compatible=False),
        grids.GridOperation("Delete", condition=(lambda item: item.deleted), async_compatible=True),
    ]

    def apply_query_filter(self, trans, query, **kwargs):
        return query.filter_by(user=trans.user, deleted=False)


class StoredWorkflowAllPublishedGrid(grids.Grid):
    title = "Published Workflows"
    model_class = model.StoredWorkflow
    default_sort_key = "update_time"
    default_filter = dict(public_url="All", username="All", tags="All")
    columns = [
        grids.PublicURLColumn("Name", key="name", filterable="advanced", attach_popup=True),
        grids.OwnerAnnotationColumn(
            "Annotation",
            key="annotation",
            model_annotation_association_class=model.StoredWorkflowAnnotationAssociation,
            filterable="advanced",
        ),
        grids.OwnerColumn("Owner", key="username", model_class=model.User, filterable="advanced"),
        grids.CommunityRatingColumn("Community Rating", key="rating"),
        grids.CommunityTagsColumn(
            "Community Tags",
            key="tags",
            model_tag_association_class=model.StoredWorkflowTagAssociation,
            filterable="advanced",
            grid_name="PublicWorkflowListGrid",
        ),
        grids.ReverseSortColumn("Last Updated", key="update_time", format=time_ago),
    ]
    columns.append(
        grids.MulticolFilterColumn(
            "Search name, annotation, owner, and tags",
            cols_to_filter=[columns[0], columns[1], columns[2], columns[4]],
            key="free-text-search",
            visible=False,
            filterable="standard",
        )
    )
    operations = [
        grids.GridOperation(
            "Run",
            condition=(lambda item: not item.deleted),
            allow_multiple=False,
            url_args=dict(controller="workflows", action="run"),
        ),
        grids.GridOperation(
            "Import", condition=(lambda item: not item.deleted), allow_multiple=False, url_args=dict(action="imp")
        ),
        grids.GridOperation(
            "Save as File",
            condition=(lambda item: not item.deleted),
            allow_multiple=False,
            url_args=dict(action="export_to_file"),
        ),
    ]
    num_rows_per_page = 50
    use_paging = True

    def build_initial_query(self, trans, **kwargs):
        # See optimization description comments and TODO for tags in matching public histories query.
        # In addition to that - be sure to lazyload the latest_workflow - it isn't needed and it causes all
        # of its steps to be eagerly loaded.
        return (
            trans.sa_session.query(self.model_class)
            .join("user")
            .options(
                lazyload("latest_workflow"),
                joinedload("user").load_only("username"),
                joinedload("annotations"),
                undefer("average_rating"),
            )
        )

    def apply_query_filter(self, trans, query, **kwargs):
        # A public workflow is published, has a slug, and is not deleted.
        return (
            query.filter(self.model_class.published == expression.true())
            .filter(self.model_class.slug.isnot(None))
            .filter(self.model_class.deleted == expression.false())
        )


# Simple HTML parser to get all content in a single tag.
class SingleTagContentsParser(HTMLParser):
    def __init__(self, target_tag):
        # Cannot use super() because HTMLParser is an old-style class in Python2
        HTMLParser.__init__(self)
        self.target_tag = target_tag
        self.cur_tag = None
        self.tag_content = ""

    def handle_starttag(self, tag, attrs):
        """Called for each start tag."""
        self.cur_tag = tag

    def handle_data(self, text):
        """Called for each block of plain text."""
        if self.cur_tag == self.target_tag:
            self.tag_content += text


class WorkflowController(BaseUIController, SharableMixin, UsesStoredWorkflowMixin, UsesItemRatings):
    stored_list_grid = StoredWorkflowListGrid()
    published_list_grid = StoredWorkflowAllPublishedGrid()
    slug_builder = SlugBuilder()

    @web.expose
    @web.require_login("use Galaxy workflows")
    def list_grid(self, trans, **kwargs):
        """List user's stored workflows."""
        # status = message = None
        if "operation" in kwargs:
            operation = kwargs["operation"].lower()
            if operation == "rename":
                return self.rename(trans, **kwargs)
            history_ids = util.listify(kwargs.get("id", []))
            if operation == "sharing":
                return self.sharing(trans, id=history_ids)
        return self.stored_list_grid(trans, **kwargs)

    @web.expose
    @web.require_login("use Galaxy workflows", use_panels=True)
    def list(self, trans):
        """
        Render workflow main page (management of existing workflows)
        """
        # Take care of proxy prefix in url as well
        redirect_url = f"{url_for('/')}workflow"
        return trans.response.send_redirect(redirect_url)

    @web.expose
    @web.json
    def list_published(self, trans, **kwargs):
        return self.published_list_grid(trans, **kwargs)

    @web.expose
    def display_by_username_and_slug(self, trans, username, slug, format="html"):
        """
        Display workflow based on a username and slug. Format can be html, json, or json-download.
        """

        # Get workflow by username and slug. Security is handled by the display methods below.
        session = trans.sa_session
        user = session.query(model.User).filter_by(username=username).first()
        if not user:
            raise web.httpexceptions.HTTPNotFound()
        stored_workflow = (
            trans.sa_session.query(model.StoredWorkflow).filter_by(user=user, slug=slug, deleted=False).first()
        )
        if not stored_workflow:
            raise web.httpexceptions.HTTPNotFound()
        encoded_id = trans.security.encode_id(stored_workflow.id)

        # Display workflow in requested format.
        if format == "html":
            return self._display(trans, stored_workflow)
        elif format == "json":
            return self.for_direct_import(trans, encoded_id)
        elif format == "json-download":
            return self.export_to_file(trans, encoded_id)

    @web.expose
    def display_by_id(self, trans, id):
        """Display workflow based on id."""
        # Get workflow.
        stored_workflow = self.get_stored_workflow(trans, id)
        return self._display(trans, stored_workflow)

    def _display(self, trans, stored_workflow):
        """Diplay workflow as HTML page."""

        if stored_workflow is None:
            raise web.httpexceptions.HTTPNotFound()
        # Security check raises error if user cannot access workflow.
        self.security_check(trans, stored_workflow, False, True)
        # Get data for workflow's steps.
        self.get_stored_workflow_steps(trans, stored_workflow)
        # Get annotations.
        stored_workflow.annotation = self.get_item_annotation_str(
            trans.sa_session, stored_workflow.user, stored_workflow
        )
        for step in stored_workflow.latest_workflow.steps:
            step.annotation = self.get_item_annotation_str(trans.sa_session, stored_workflow.user, step)
        user_is_owner = True if trans.user == stored_workflow.user else False
        # Get rating data.
        user_item_rating = 0
        if trans.get_user():
            user_item_rating = self.get_user_item_rating(trans.sa_session, trans.get_user(), stored_workflow)
            if user_item_rating:
                user_item_rating = user_item_rating.rating
            else:
                user_item_rating = 0
        ave_item_rating, num_ratings = self.get_ave_item_rating_data(trans.sa_session, stored_workflow)
        return trans.fill_template_mako(
            "workflow/display.mako",
            item=stored_workflow,
            item_data=stored_workflow.latest_workflow.steps,
            user_item_rating=user_item_rating,
            ave_item_rating=ave_item_rating,
            num_ratings=num_ratings,
            user_is_owner=user_is_owner,
        )

    @web.expose
    def get_item_content_async(self, trans, id):
        """Returns item content in HTML format."""

        stored = self.get_stored_workflow(trans, id, False, True)
        if stored is None:
            raise web.httpexceptions.HTTPNotFound()

        # Get data for workflow's steps.
        self.get_stored_workflow_steps(trans, stored)
        # Get annotations.
        stored.annotation = self.get_item_annotation_str(trans.sa_session, stored.user, stored)
        for step in stored.latest_workflow.steps:
            step.annotation = self.get_item_annotation_str(trans.sa_session, stored.user, step)
        return trans.fill_template_mako(
            "/workflow/item_content.mako", item=stored, item_data=stored.latest_workflow.steps
        )

    @web.expose
    @web.require_login("use Galaxy workflows")
    def share(self, trans, id, email="", use_panels=False):
        msg = mtype = None
        # Load workflow from database
        stored = self.get_stored_workflow(trans, id)
        if email:
            other = (
                trans.sa_session.query(model.User)
                .filter(and_(model.User.table.c.email == email, model.User.table.c.deleted == expression.false()))
                .first()
            )
            if not other:
                mtype = "error"
                msg = f"User '{escape(email)}' does not exist"
            elif other == trans.get_user():
                mtype = "error"
                msg = "You cannot share a workflow with yourself"
            elif (
                trans.sa_session.query(model.StoredWorkflowUserShareAssociation)
                .filter_by(user=other, stored_workflow=stored)
                .count()
                > 0
            ):
                mtype = "error"
                msg = f"Workflow already shared with '{escape(email)}'"
            else:
                share = model.StoredWorkflowUserShareAssociation()
                share.stored_workflow = stored
                share.user = other
                session = trans.sa_session
                session.add(share)
                session.flush()
                trans.set_message(f"Workflow '{escape(stored.name)}' shared with user '{escape(other.email)}'")
                return trans.response.send_redirect(url_for(controller="workflow", action="sharing", id=id))
        return trans.fill_template(
            "/ind_share_base.mako", message=msg, messagetype=mtype, item=stored, email=email, use_panels=use_panels
        )

    @web.expose
    @web.require_login("export Galaxy workflows")
    def export(self, trans, id, **kwargs):
        """Handle workflow export."""
        session = trans.sa_session
        # Get session and workflow.
        stored = self.get_stored_workflow(trans, id)
        session.add(stored)

        # Legacy issue: workflows made accessible before recent updates may not have a slug. Create slug for any workflows that need them.
        if stored.importable and not stored.slug:
            self._make_item_accessible(trans.sa_session, stored)

        session.flush()
        return trans.fill_template("/workflow/sharing.mako", use_panels=True, item=stored)

    @web.expose
    @web.require_login("to import a workflow", use_panels=True)
    def imp(self, trans, id, **kwargs):
        """Imports a workflow shared by other users."""
        # Set referer message.
        referer = trans.request.referer
        if referer and not referer.startswith(f"{trans.request.application_url}{url_for('/login')}"):
            referer_message = f"<a href='{escape(referer)}'>return to the previous page</a>"
        else:
            referer_message = f"<a href='{url_for('/')}'>go to Galaxy's start page</a>"

        # Do import.
        stored = self.get_stored_workflow(trans, id, check_ownership=False)
        if stored.importable is False:
            return trans.show_error_message(
                f"The owner of this workflow has disabled imports via this link.<br>You can {referer_message}",
                use_panels=True,
            )
        elif stored.deleted:
            return trans.show_error_message(
                f"You can't import this workflow because it has been deleted.<br>You can {referer_message}",
                use_panels=True,
            )
        self._import_shared_workflow(trans, stored)

        # Redirect to load galaxy frames.
        return trans.show_ok_message(
            message="""Workflow "%s" has been imported. <br>You can <a href="%s">start using this workflow</a> or %s."""
            % (stored.name, web.url_for("/workflows/list"), referer_message)
        )

    @web.expose
    @web.require_login("use Galaxy workflows")
    def rename_async(self, trans, id, new_name=None, **kwargs):
        stored = self.get_stored_workflow(trans, id)
        if new_name:
            san_new_name = sanitize_html(new_name)
            stored.name = san_new_name
            stored.latest_workflow.name = san_new_name
            trans.sa_session.flush()
            return stored.name

    @web.expose
    @web.require_login("use Galaxy workflows")
    def annotate_async(self, trans, id, new_annotation=None, **kwargs):
        stored = self.get_stored_workflow(trans, id)
        if new_annotation:
            # Sanitize annotation before adding it.
            new_annotation = sanitize_html(new_annotation)
            self.add_item_annotation(trans.sa_session, trans.get_user(), stored, new_annotation)
            trans.sa_session.flush()
            return new_annotation

    @web.expose
    @web.require_login("rate items")
    @web.json
    def rate_async(self, trans, id, rating):
        """Rate a workflow asynchronously and return updated community data."""

        stored = self.get_stored_workflow(trans, id, check_ownership=False, check_accessible=True)
        if not stored:
            return trans.show_error_message("The specified workflow does not exist.")

        # Rate workflow.
        self.rate_item(trans.sa_session, trans.get_user(), stored, rating)

        return self.get_ave_item_rating_data(trans.sa_session, stored)

    @web.expose
    def get_embed_html_async(self, trans, id):
        """Returns HTML for embedding a workflow in a page."""

        # TODO: user should be able to embed any item he has access to. see display_by_username_and_slug for security code.
        stored = self.get_stored_workflow(trans, id)
        if stored:
            return f"Embedded Workflow '{stored.name}'"

    @web.expose
    @web.json
    @web.require_login("use Galaxy workflows")
    def get_name_and_link_async(self, trans, id=None):
        """Returns workflow's name and link."""
        stored = self.get_stored_workflow(trans, id)

        return_dict = {
            "name": stored.name,
            "link": url_for(
                controller="workflow",
                action="display_by_username_and_slug",
                username=stored.user.username,
                slug=stored.slug,
            ),
        }
        return return_dict

    @web.expose
    @web.require_login("use Galaxy workflows")
    def gen_image(self, trans, id):
        stored = self.get_stored_workflow(trans, id, check_ownership=True)
        try:
            svg = self._workflow_to_svg_canvas(trans, stored)
        except Exception:
            status = "error"
            message = (
                "Galaxy is unable to create the SVG image. Please check your workflow, there might be missing tools."
            )
            return trans.fill_template(
                "/workflow/sharing.mako", use_panels=True, item=stored, status=status, message=message
            )
        trans.response.set_content_type("image/svg+xml")
        s = STANDALONE_SVG_TEMPLATE % svg.tostring()
        return s.encode("utf-8")

    @web.expose
    @web.require_login("use Galaxy workflows")
    def copy(self, trans, id, save_as_name=None):
        # Get workflow to copy.
        stored = self.get_stored_workflow(trans, id, check_ownership=False)
        user = trans.get_user()
        if stored.user == user:
            owner = True
        else:
            if (
                trans.sa_session.query(model.StoredWorkflowUserShareAssociation)
                .filter_by(user=user, stored_workflow=stored)
                .count()
                == 0
            ):
                error("Workflow is not owned by or shared with current user")
            owner = False

        # Copy.
        new_stored = model.StoredWorkflow()
        if save_as_name:
            new_stored.name = f"{save_as_name}"
        else:
            new_stored.name = f"Copy of {stored.name}"
        new_stored.latest_workflow = stored.latest_workflow
        # Copy annotation.
        annotation_obj = self.get_item_annotation_obj(trans.sa_session, stored.user, stored)
        if annotation_obj:
            self.add_item_annotation(trans.sa_session, trans.get_user(), new_stored, annotation_obj.annotation)
        new_stored.copy_tags_from(trans.user, stored)
        if not owner:
            new_stored.name += f" shared by {stored.user.email}"
        new_stored.user = user
        # Persist
        session = trans.sa_session
        session.add(new_stored)
        session.flush()
        # Display the management page
        message = f"Created new workflow with name: {escape(new_stored.name)}"
        trans.set_message(message)
        return_url = f"{url_for('/')}workflow?status=done&message={escape(message)}"
        trans.response.send_redirect(return_url)

    @web.legacy_expose_api
    def create(self, trans, payload=None, **kwd):
        if trans.request.method == "GET":
            return {
                "title": "Create Workflow",
                "inputs": [
                    {"name": "workflow_name", "label": "Name", "value": "Unnamed workflow"},
                    {
                        "name": "workflow_annotation",
                        "label": "Annotation",
                        "help": "A description of the workflow; annotation is shown alongside shared or published workflows.",
                    },
                ],
            }
        else:
            user = trans.get_user()
            workflow_name = payload.get("workflow_name")
            workflow_annotation = payload.get("workflow_annotation")
            if not workflow_name:
                return self.message_exception(trans, "Please provide a workflow name.")
            # Create the new stored workflow
            stored_workflow = model.StoredWorkflow()
            stored_workflow.name = workflow_name
            stored_workflow.user = user
            self.slug_builder.create_item_slug(trans.sa_session, stored_workflow)
            # And the first (empty) workflow revision
            workflow = model.Workflow()
            workflow.name = workflow_name
            workflow.stored_workflow = stored_workflow
            stored_workflow.latest_workflow = workflow
            # Add annotation.
            workflow_annotation = sanitize_html(workflow_annotation)
            self.add_item_annotation(trans.sa_session, trans.get_user(), stored_workflow, workflow_annotation)
            # Persist
            session = trans.sa_session
            session.add(stored_workflow)
            session.flush()
            return {
                "id": trans.security.encode_id(stored_workflow.id),
                "message": f"Workflow {workflow_name} has been created.",
            }

    @web.json
    def save_workflow_as(self, trans, workflow_name, workflow_data, workflow_annotation="", from_tool_form=False):
        """
        Creates a new workflow based on Save As command. It is a new workflow, but
        is created with workflow_data already present.
        """
        user = trans.get_user()
        if workflow_name is not None:
            workflow_contents_manager = self.app.workflow_contents_manager
            stored_workflow = model.StoredWorkflow()
            stored_workflow.name = workflow_name
            stored_workflow.user = user
            self.slug_builder.create_item_slug(trans.sa_session, stored_workflow)
            workflow = model.Workflow()
            workflow.name = workflow_name
            workflow.stored_workflow = stored_workflow
            stored_workflow.latest_workflow = workflow
            # Add annotation.
            workflow_annotation = sanitize_html(workflow_annotation)
            self.add_item_annotation(trans.sa_session, trans.get_user(), stored_workflow, workflow_annotation)

            # Persist
            session = trans.sa_session
            session.add(stored_workflow)
            session.flush()
            workflow_update_options = WorkflowUpdateOptions(
                update_stored_workflow_attributes=False,  # taken care of above
                from_tool_form=from_tool_form,
            )
            try:
                workflow, errors = workflow_contents_manager.update_workflow_from_raw_description(
                    trans,
                    stored_workflow,
                    workflow_data,
                    workflow_update_options,
                )
            except MissingToolsException as e:
                return dict(
                    name=e.workflow.name,
                    message=(
                        "This workflow includes missing or invalid tools. "
                        "It cannot be saved until the following steps are removed or the missing tools are enabled."
                    ),
                    errors=e.errors,
                )
            return trans.security.encode_id(stored_workflow.id)
        else:
            # This is an error state, 'save as' must have a workflow_name
            log.exception("Error in Save As workflow: no name.")

    @web.expose
    def delete(self, trans, id=None):
        """
        Mark a workflow as deleted
        """
        # Load workflow from database
        stored = self.get_stored_workflow(trans, id)
        # Mark as deleted and save
        stored.deleted = True
        trans.user.stored_workflow_menu_entries = [
            entry for entry in trans.user.stored_workflow_menu_entries if entry.stored_workflow != stored
        ]
        trans.sa_session.add(stored)
        trans.sa_session.flush()
        # Display the management page
        message = f"Workflow deleted: {escape(stored.name)}"
        trans.set_message(message)
        return trans.response.send_redirect(f"{url_for('/')}workflow?status=done&message={escape(message)}")

    @web.expose
    @web.require_login("edit workflows")
    def editor(self, trans, id=None, workflow_id=None, version=None):
        """
        Render the main workflow editor interface. The canvas is embedded as
        an iframe (necessary for scrolling to work properly), which is
        rendered by `editor_canvas`.
        """
        if not id:
            if workflow_id:
                stored_workflow = self.app.workflow_manager.get_stored_workflow(trans, workflow_id, by_stored_id=False)
                self.security_check(trans, stored_workflow, True, False)
                stored_workflow_id = trans.security.encode_id(stored_workflow.id)
                return trans.response.send_redirect(f'{url_for("/")}workflow/editor?id={stored_workflow_id}')

            error("Invalid workflow id")
        stored = self.get_stored_workflow(trans, id)
        # The following query loads all user-owned workflows,
        # So that they can be copied or inserted in the workflow editor.
        workflows = (
            trans.sa_session.query(model.StoredWorkflow)
            .filter_by(user=trans.user, deleted=False, hidden=False)
            .order_by(desc(model.StoredWorkflow.table.c.update_time))
            .options(joinedload("latest_workflow").joinedload("steps"))
            .all()
        )
        if version is None:
            version = len(stored.workflows) - 1
        else:
            version = int(version)

        # create workflow module models
        module_sections = []
        for module_section in load_module_sections(trans).values():
            module_sections.append(
                {
                    "title": module_section.get("title"),
                    "name": module_section.get("name"),
                    "elems": [
                        {"name": elem.get("name"), "title": elem.get("title"), "description": elem.get("description")}
                        for elem in module_section.get("modules")
                    ],
                }
            )

        # create data manager tool models
        data_managers = []
        if trans.user_is_admin and trans.app.data_managers.data_managers:
            for data_manager_val in trans.app.data_managers.data_managers.values():
                tool = data_manager_val.tool
                if not tool.hidden:
                    data_managers.append(
                        {
                            "id": tool.id,
                            "name": tool.name,
                            "hidden": tool.hidden,
                            "description": tool.description,
                            "is_workflow_compatible": tool.is_workflow_compatible,
                        }
                    )

        # create workflow models
        workflows = [
            {
                "id": trans.security.encode_id(workflow.id),
                "latest_id": trans.security.encode_id(workflow.latest_workflow.id),
                "step_count": len(workflow.latest_workflow.steps),
                "name": workflow.name,
            }
            for workflow in workflows
            if workflow.id != stored.id
        ]

        # identify item tags
        item_tags = [tag for tag in stored.tags if tag.user == trans.user]
        item_tag_names = []
        for ta in item_tags:
            item_tag_names.append(escape(ta.tag.name))

        # build workflow editor model
        editor_config = {
            "id": trans.security.encode_id(stored.id),
            "name": stored.name,
            "tags": item_tag_names,
            "initialVersion": version,
            "annotation": self.get_item_annotation_str(trans.sa_session, trans.user, stored),
            "moduleSections": module_sections,
            "dataManagers": data_managers,
            "workflows": workflows,
        }

        # parse to mako
        return trans.fill_template("workflow/editor.mako", editor_config=editor_config)

    @web.json
    def load_workflow(self, trans, id, version=None):
        """
        Get the latest Workflow for the StoredWorkflow identified by `id` and
        encode it as a json string that can be read by the workflow editor
        web interface.
        """
        trans.workflow_building_mode = workflow_building_modes.ENABLED
        stored = self.get_stored_workflow(trans, id, check_ownership=True, check_accessible=False)
        workflow_contents_manager = self.app.workflow_contents_manager
        return workflow_contents_manager.workflow_to_dict(trans, stored, style="editor", version=version)

    @web.expose
    @web.require_login("use workflows")
    def export_to_myexp(self, trans, id, myexp_username, myexp_password):
        """
        Exports a workflow to myExperiment website.
        """
        trans.workflow_building_mode = workflow_building_modes.ENABLED
        stored = self.get_stored_workflow(trans, id, check_ownership=False, check_accessible=True)

        # Convert workflow to dict.
        workflow_dict = self._workflow_to_dict(trans, stored)

        #
        # Create and submit workflow myExperiment request.
        #

        # Create workflow content JSON.
        workflow_content = json.dumps(workflow_dict, indent=4, sort_keys=True)

        # Create myExperiment request.
        request_raw = trans.fill_template(
            "workflow/myexp_export.mako",
            workflow_name=workflow_dict["name"],
            workflow_description=workflow_dict["annotation"],
            workflow_content=workflow_content,
            workflow_svg=self._workflow_to_svg_canvas(trans, stored).tostring(),
        )
        # strip() b/c myExperiment XML parser doesn't allow white space before XML; utf-8 handles unicode characters.
        request = unicodify(request_raw.strip(), "utf-8")

        # Do request and get result.
        auth_header = base64.b64encode(f"{myexp_username}:{myexp_password}")
        headers = {"Content-type": "text/xml", "Accept": "text/xml", "Authorization": f"Basic {auth_header}"}
        myexp_url = trans.app.config.myexperiment_target_url
        conn = HTTPConnection(myexp_url)
        # NOTE: blocks web thread.
        conn.request("POST", "/workflow.xml", request, headers)
        response = conn.getresponse()
        response_data = response.read()
        conn.close()

        # Do simple parse of response to see if export successful and provide user feedback.
        parser = SingleTagContentsParser("id")
        parser.feed(response_data)
        myexp_workflow_id = parser.tag_content
        workflow_list_str = f" <br>Return to <a href='{url_for(controller='workflows', action='list')}'>workflow list."
        if myexp_workflow_id:
            return trans.show_message(
                """Workflow '{}' successfully exported to myExperiment. <br/>
                <a href="http://{}/workflows/{}">Click here to view the workflow on myExperiment</a> {}
                """.format(
                    stored.name, myexp_url, myexp_workflow_id, workflow_list_str
                ),
                use_panels=True,
            )
        else:
            return trans.show_error_message(
                "Workflow '%s' could not be exported to myExperiment. Error: %s %s"
                % (stored.name, response_data, workflow_list_str),
                use_panels=True,
            )

    @web.json_pretty
    def for_direct_import(self, trans, id):
        """
        Get the latest Workflow for the StoredWorkflow identified by `id` and
        encode it as a json string that can be imported back into Galaxy

        This has slightly different information than the above. In particular,
        it does not attempt to decode forms and build UIs, it just stores
        the raw state.
        """
        stored = self.get_stored_workflow(trans, id, check_ownership=False, check_accessible=True)
        return self._workflow_to_dict(trans, stored)

    @web.json_pretty
    def export_to_file(self, trans, id):
        """
        Get the latest Workflow for the StoredWorkflow identified by `id` and
        encode it as a json string that can be imported back into Galaxy

        This has slightly different information than the above. In particular,
        it does not attempt to decode forms and build UIs, it just stores
        the raw state.
        """

        # Get workflow.
        stored = self.get_stored_workflow(trans, id, check_ownership=False, check_accessible=True)

        # Stream workflow to file.
        stored_dict = self._workflow_to_dict(trans, stored)
        if not stored_dict:
            # This workflow has a tool that's missing from the distribution
            trans.response.status = 400
            return "Workflow cannot be exported due to missing tools."
        sname = stored.name
        sname = "".join(c in FILENAME_VALID_CHARS and c or "_" for c in sname)[0:150]
        trans.response.headers["Content-Disposition"] = f'attachment; filename="Galaxy-Workflow-{sname}.ga"'
        trans.response.set_content_type("application/galaxy-archive")
        return stored_dict

    @web.expose
    def build_from_current_history(
        self,
        trans,
        job_ids=None,
        dataset_ids=None,
        dataset_collection_ids=None,
        workflow_name=None,
        dataset_names=None,
        dataset_collection_names=None,
    ):
        user = trans.get_user()
        history = trans.get_history()
        if not user:
            return trans.show_error_message("Must be logged in to create workflows")
        if (job_ids is None and dataset_ids is None) or workflow_name is None:
            jobs, warnings = summarize(trans)
            # Render
            return trans.fill_template(
                "workflow/build_from_current_history.mako", jobs=jobs, warnings=warnings, history=history
            )
        else:
            # If there is just one dataset name selected or one dataset collection, these
            # come through as string types instead of lists. xref #3247.
            dataset_names = util.listify(dataset_names)
            dataset_collection_names = util.listify(dataset_collection_names)
            stored_workflow = extract_workflow(
                trans,
                user=user,
                job_ids=job_ids,
                dataset_ids=dataset_ids,
                dataset_collection_ids=dataset_collection_ids,
                workflow_name=workflow_name,
                dataset_names=dataset_names,
                dataset_collection_names=dataset_collection_names,
            )
            # Index page with message
            workflow_id = trans.security.encode_id(stored_workflow.id)
            return trans.show_message(
                'Workflow "%s" created from current history. '
                'You can <a href="%s" target="_parent">edit</a> or <a href="%s" target="_parent">run</a> the workflow.'
                % (
                    escape(workflow_name),
                    url_for(controller="workflow", action="editor", id=workflow_id),
                    url_for(controller="workflows", action="run", id=workflow_id),
                )
            )

    def get_item(self, trans, id):
        return self.get_stored_workflow(trans, id)

    def _workflow_to_svg_canvas(self, trans, stored):
        workflow = stored.latest_workflow
        workflow_canvas = WorkflowCanvas()
        for step in workflow.steps:
            # Load from database representation
            module = module_factory.from_workflow_step(trans, step)
            module_name = module.get_name()
            module_data_inputs = module.get_data_inputs()
            module_data_outputs = module.get_data_outputs()
            workflow_canvas.populate_data_for_step(
                step,
                module_name,
                module_data_inputs,
                module_data_outputs,
            )
        workflow_canvas.add_steps()
        return workflow_canvas.finish()
