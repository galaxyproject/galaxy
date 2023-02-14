import logging
from html.parser import HTMLParser

from markupsafe import escape
from sqlalchemy import desc
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
from galaxy.util import FILENAME_VALID_CHARS
from galaxy.util.sanitize_html import sanitize_html
from galaxy.web import url_for
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
            .join(self.model_class.user)
            .options(
                lazyload(self.model_class.latest_workflow),
                joinedload(self.model_class.user).load_only(model.User.username),
                joinedload(self.model_class.annotations),
                undefer(self.model_class.average_rating),
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
            workflow_ids = util.listify(kwargs.get("id", []))
            if operation == "sharing":
                return self.sharing(trans, id=workflow_ids)
        return self.stored_list_grid(trans, **kwargs)

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

    def _display(self, trans, stored_workflow):
        """Diplay workflow in client."""
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

        # Encode page identifier.
        workflow_id = trans.security.encode_id(stored_workflow.id)

        # Redirect to client.
        return trans.response.send_redirect(
            web.url_for(
                controller="published",
                action="workflow",
                id=workflow_id,
            )
        )

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
            message = (
                "Galaxy is unable to create the SVG image. Please check your workflow, there might be missing tools."
            )
            return trans.show_error_message(message)
        trans.response.set_content_type("image/svg+xml")
        s = STANDALONE_SVG_TEMPLATE % svg.tostring()
        return s.encode("utf-8")

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
    @web.json
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
                id = trans.security.encode_id(stored_workflow.id)
        stored = self.get_stored_workflow(trans, id)
        # The following query loads all user-owned workflows,
        # So that they can be copied or inserted in the workflow editor.
        workflows = (
            trans.sa_session.query(model.StoredWorkflow)
            .filter_by(user=trans.user, deleted=False, hidden=False)
            .order_by(desc(model.StoredWorkflow.table.c.update_time))
            .options(joinedload(model.StoredWorkflow.latest_workflow).joinedload(model.Workflow.steps))
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
        item_tags = stored.make_tag_string_list()

        # build workflow editor model
        editor_config = {
            "id": trans.security.encode_id(stored.id),
            "name": stored.name,
            "tags": item_tags,
            "initialVersion": version,
            "annotation": self.get_item_annotation_str(trans.sa_session, trans.user, stored),
            "moduleSections": module_sections,
            "dataManagers": data_managers,
            "workflows": workflows,
        }

        # parse to mako
        return editor_config

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
            edit_url = url_for(f"/workflows/edit?id={workflow_id}")
            run_url = url_for(f"/workflows/run?id={workflow_id}")
            return trans.show_message(
                f'Workflow "{escape(workflow_name)}" created from current history. '
                f'You can <a href="{edit_url}" target="_parent">edit</a> or <a href="{run_url}" target="_parent">run</a> the workflow.'
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
