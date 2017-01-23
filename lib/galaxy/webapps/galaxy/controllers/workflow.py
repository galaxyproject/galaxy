import base64
import httplib
import json
import logging
import os
import sgmllib
import urllib2

from sqlalchemy import and_
from sqlalchemy.sql import expression
from markupsafe import escape

from tool_shed.util import encoding_util

from galaxy import model
from galaxy import util
from galaxy import web
from galaxy import exceptions
from galaxy.managers import workflows, histories
from galaxy.model.item_attrs import UsesItemRatings
from galaxy.model.mapping import desc
from galaxy.util import unicodify, FILENAME_VALID_CHARS
from galaxy.util.sanitize_html import sanitize_html
from galaxy.web import error, url_for
from galaxy.web.base.controller import BaseUIController, SharableMixin, UsesStoredWorkflowMixin
from galaxy.web.framework.formbuilder import form
from galaxy.web.framework.helpers import grids, time_ago, to_unicode
from galaxy.workflow.extract import extract_workflow
from galaxy.workflow.extract import summarize
from galaxy.workflow.modules import module_factory
from galaxy.workflow.modules import WorkflowModuleInjector
from galaxy.workflow.render import WorkflowCanvas, STANDALONE_SVG_TEMPLATE

log = logging.getLogger( __name__ )


class StoredWorkflowListGrid( grids.Grid ):

    class StepsColumn( grids.GridColumn ):
        def get_value(self, trans, grid, workflow):
            return len( workflow.latest_workflow.steps )

    # Grid definition
    use_panels = True
    title = "Saved Workflows"
    model_class = model.StoredWorkflow
    default_filter = { "name": "All", "tags": "All" }
    default_sort_key = "-update_time"
    columns = [
        grids.TextColumn( "Name", key="name", attach_popup=True, filterable="advanced" ),
        grids.IndividualTagsColumn( "Tags",
                                    "tags",
                                    model_tag_association_class=model.StoredWorkflowTagAssociation,
                                    filterable="advanced",
                                    grid_name="StoredWorkflowListGrid" ),
        StepsColumn( "Steps" ),
        grids.GridColumn( "Created", key="create_time", format=time_ago ),
        grids.GridColumn( "Last Updated", key="update_time", format=time_ago ),
    ]
    columns.append(
        grids.MulticolFilterColumn(
            "Search",
            cols_to_filter=[ columns[0], columns[1] ],
            key="free-text-search", visible=False, filterable="standard"
        )
    )
    operations = [
        grids.GridOperation( "Edit", allow_multiple=False, condition=( lambda item: not item.deleted ), async_compatible=False ),
        grids.GridOperation( "Run", condition=( lambda item: not item.deleted ), async_compatible=False ),
        grids.GridOperation( "Copy", condition=( lambda item: not item.deleted ), async_compatible=False  ),
        grids.GridOperation( "Rename", condition=( lambda item: not item.deleted ), async_compatible=False  ),
        grids.GridOperation( "Sharing", condition=( lambda item: not item.deleted ), async_compatible=False ),
        grids.GridOperation( "Delete", condition=( lambda item: item.deleted ), async_compatible=True ),
    ]

    def apply_query_filter( self, trans, query, **kwargs ):
        return query.filter_by( user=trans.user, deleted=False )


class StoredWorkflowAllPublishedGrid( grids.Grid ):
    title = "Published Workflows"
    model_class = model.StoredWorkflow
    default_sort_key = "update_time"
    default_filter = dict( public_url="All", username="All", tags="All" )
    use_async = True
    columns = [
        grids.PublicURLColumn( "Name", key="name", filterable="advanced", attach_popup=True ),
        grids.OwnerAnnotationColumn( "Annotation",
                                     key="annotation",
                                     model_annotation_association_class=model.StoredWorkflowAnnotationAssociation,
                                     filterable="advanced" ),
        grids.OwnerColumn( "Owner", key="username", model_class=model.User, filterable="advanced" ),
        grids.CommunityRatingColumn( "Community Rating", key="rating" ),
        grids.CommunityTagsColumn( "Community Tags", key="tags",
                                   model_tag_association_class=model.StoredWorkflowTagAssociation,
                                   filterable="advanced", grid_name="PublicWorkflowListGrid" ),
        grids.ReverseSortColumn( "Last Updated", key="update_time", format=time_ago )
    ]
    columns.append(
        grids.MulticolFilterColumn(
            "Search name, annotation, owner, and tags",
            cols_to_filter=[ columns[0], columns[1], columns[2], columns[4] ],
            key="free-text-search", visible=False, filterable="standard"
        )
    )
    operations = [
        grids.GridOperation(
            "Import",
            condition=( lambda item: not item.deleted ),
            allow_multiple=False,
            url_args=dict( action="imp")
        ),
        grids.GridOperation(
            "Save as File",
            condition=( lambda item: not item.deleted ),
            allow_multiple=False,
            url_args=dict( action="export_to_file" )
        ),
    ]

    def build_initial_query( self, trans, **kwargs ):
        # Join so that searching stored_workflow.user makes sense.
        return trans.sa_session.query( self.model_class ).join( model.User.table )

    def apply_query_filter( self, trans, query, **kwargs ):
        # A public workflow is published, has a slug, and is not deleted.
        return query.filter(
            self.model_class.published == expression.true() ).filter(
            self.model_class.slug.isnot(None)).filter(
            self.model_class.deleted == expression.false())


# Simple SGML parser to get all content in a single tag.
class SingleTagContentsParser( sgmllib.SGMLParser ):

    def __init__( self, target_tag ):
        sgmllib.SGMLParser.__init__( self )
        self.target_tag = target_tag
        self.cur_tag = None
        self.tag_content = ""

    def unknown_starttag( self, tag, attrs ):
        """ Called for each start tag. """
        self.cur_tag = tag

    def handle_data( self, text ):
        """ Called for each block of plain text. """
        if self.cur_tag == self.target_tag:
            self.tag_content += text


class WorkflowController( BaseUIController, SharableMixin, UsesStoredWorkflowMixin, UsesItemRatings ):
    stored_list_grid = StoredWorkflowListGrid()
    published_list_grid = StoredWorkflowAllPublishedGrid()

    __myexp_url = "www.myexperiment.org:80"

    @web.expose
    def index( self, trans ):
        return self.list( trans )

    @web.expose
    @web.require_login( "use Galaxy workflows" )
    def list_grid( self, trans, **kwargs ):
        """ List user's stored workflows. """
        # status = message = None
        if 'operation' in kwargs:
            operation = kwargs['operation'].lower()
            if operation == "rename":
                return self.rename( trans, **kwargs )
            history_ids = util.listify( kwargs.get( 'id', [] ) )
            if operation == "sharing":
                return self.sharing( trans, id=history_ids )
        return self.stored_list_grid( trans, **kwargs )

    @web.expose
    @web.require_login( "use Galaxy workflows", use_panels=True )
    def list( self, trans ):
        """
        Render workflow main page (management of existing workflows)
        """
        user = trans.get_user()
        workflows = trans.sa_session.query( model.StoredWorkflow ) \
            .filter_by( user=user, deleted=False ) \
            .order_by( desc( model.StoredWorkflow.table.c.update_time ) ) \
            .all()
        shared_by_others = trans.sa_session \
            .query( model.StoredWorkflowUserShareAssociation ) \
            .filter_by( user=user ) \
            .join( 'stored_workflow' ) \
            .filter( model.StoredWorkflow.deleted == expression.false() ) \
            .order_by( desc( model.StoredWorkflow.update_time ) ) \
            .all()

        # Legacy issue: all shared workflows must have slugs.
        slug_set = False
        for workflow_assoc in shared_by_others:
            if self.create_item_slug( trans.sa_session, workflow_assoc.stored_workflow ):
                slug_set = True
        if slug_set:
            trans.sa_session.flush()

        return trans.fill_template( "workflow/list.mako",
                                    workflows=workflows,
                                    shared_by_others=shared_by_others )

    @web.expose
    @web.require_login( "use Galaxy workflows" )
    def list_for_run( self, trans ):
        """
        Render workflow list for analysis view (just allows running workflow
        or switching to management view)
        """
        user = trans.get_user()
        workflows = trans.sa_session.query( model.StoredWorkflow ) \
            .filter_by( user=user, deleted=False ) \
            .order_by( desc( model.StoredWorkflow.table.c.update_time ) ) \
            .all()
        shared_by_others = trans.sa_session \
            .query( model.StoredWorkflowUserShareAssociation ) \
            .filter_by( user=user ) \
            .filter( model.StoredWorkflow.deleted == expression.false() ) \
            .order_by( desc( model.StoredWorkflow.table.c.update_time ) ) \
            .all()
        return trans.fill_template( "workflow/list_for_run.mako",
                                    workflows=workflows,
                                    shared_by_others=shared_by_others )

    @web.expose
    def list_published( self, trans, **kwargs ):
        kwargs[ 'embedded' ] = True
        grid = self.published_list_grid( trans, **kwargs )
        if 'async' in kwargs:
            return grid

        # Render grid wrapped in panels
        return trans.fill_template( "workflow/list_published.mako", embedded_grid=grid )

    @web.expose
    def display_by_username_and_slug( self, trans, username, slug, format='html' ):
        """
        Display workflow based on a username and slug. Format can be html, json, or json-download.
        """

        # Get workflow by username and slug. Security is handled by the display methods below.
        session = trans.sa_session
        user = session.query( model.User ).filter_by( username=username ).first()
        if not user:
            raise web.httpexceptions.HTTPNotFound()
        stored_workflow = trans.sa_session.query( model.StoredWorkflow ).filter_by( user=user, slug=slug, deleted=False ).first()
        if not stored_workflow:
            raise web.httpexceptions.HTTPNotFound()
        encoded_id = trans.security.encode_id( stored_workflow.id )

        # Display workflow in requested format.
        if format == 'html':
            return self._display( trans, stored_workflow )
        elif format == 'json':
            return self.for_direct_import( trans, encoded_id )
        elif format == 'json-download':
            return self.export_to_file( trans, encoded_id )

    @web.expose
    def display_by_id( self, trans, id ):
        """ Display workflow based on id. """
        # Get workflow.
        stored_workflow = self.get_stored_workflow( trans, id )
        return self._display(trans, stored_workflow)

    def _display( self, trans, stored_workflow ):
        """ Diplay workflow as HTML page. """

        if stored_workflow is None:
            raise web.httpexceptions.HTTPNotFound()
        # Security check raises error if user cannot access workflow.
        self.security_check( trans, stored_workflow, False, True )
        # Get data for workflow's steps.
        self.get_stored_workflow_steps( trans, stored_workflow )
        # Get annotations.
        stored_workflow.annotation = self.get_item_annotation_str( trans.sa_session, stored_workflow.user, stored_workflow )
        for step in stored_workflow.latest_workflow.steps:
            step.annotation = self.get_item_annotation_str( trans.sa_session, stored_workflow.user, step )
        # Get rating data.
        user_item_rating = 0
        if trans.get_user():
            user_item_rating = self.get_user_item_rating( trans.sa_session, trans.get_user(), stored_workflow )
            if user_item_rating:
                user_item_rating = user_item_rating.rating
            else:
                user_item_rating = 0
        ave_item_rating, num_ratings = self.get_ave_item_rating_data( trans.sa_session, stored_workflow )
        return trans.fill_template_mako( "workflow/display.mako", item=stored_workflow, item_data=stored_workflow.latest_workflow.steps,
                                         user_item_rating=user_item_rating, ave_item_rating=ave_item_rating, num_ratings=num_ratings )

    @web.expose
    def get_item_content_async( self, trans, id ):
        """ Returns item content in HTML format. """

        stored = self.get_stored_workflow( trans, id, False, True )
        if stored is None:
            raise web.httpexceptions.HTTPNotFound()

        # Get data for workflow's steps.
        self.get_stored_workflow_steps( trans, stored )
        # Get annotations.
        stored.annotation = self.get_item_annotation_str( trans.sa_session, stored.user, stored )
        for step in stored.latest_workflow.steps:
            step.annotation = self.get_item_annotation_str( trans.sa_session, stored.user, step )
        return trans.stream_template_mako( "/workflow/item_content.mako", item=stored, item_data=stored.latest_workflow.steps )

    @web.expose
    @web.require_login( "use Galaxy workflows" )
    def share( self, trans, id, email="", use_panels=False ):
        msg = mtype = None
        # Load workflow from database
        stored = self.get_stored_workflow( trans, id )
        if email:
            other = trans.sa_session.query( model.User ) \
                                    .filter( and_( model.User.table.c.email == email,
                                                   model.User.table.c.deleted == expression.false() ) ) \
                                    .first()
            if not other:
                mtype = "error"
                msg = ( "User '%s' does not exist" % escape( email ) )
            elif other == trans.get_user():
                mtype = "error"
                msg = ( "You cannot share a workflow with yourself" )
            elif trans.sa_session.query( model.StoredWorkflowUserShareAssociation ) \
                    .filter_by( user=other, stored_workflow=stored ).count() > 0:
                mtype = "error"
                msg = ( "Workflow already shared with '%s'" % escape( email ) )
            else:
                share = model.StoredWorkflowUserShareAssociation()
                share.stored_workflow = stored
                share.user = other
                session = trans.sa_session
                session.add( share )
                session.flush()
                trans.set_message( "Workflow '%s' shared with user '%s'" % ( escape( stored.name ), escape( other.email ) ) )
                return trans.response.send_redirect( url_for( controller='workflow', action='sharing', id=id ) )
        return trans.fill_template( "/ind_share_base.mako",
                                    message=msg,
                                    messagetype=mtype,
                                    item=stored,
                                    email=email,
                                    use_panels=use_panels )

    @web.expose
    @web.require_login( "Share or export Galaxy workflows" )
    def sharing( self, trans, id, **kwargs ):
        """ Handle workflow sharing. """
        session = trans.sa_session
        if 'unshare_me' in kwargs:
            # Remove self from shared associations with workflow.
            stored = self.get_stored_workflow(trans, id, False, True)
            association = session.query( model.StoredWorkflowUserShareAssociation ) \
                                 .filter_by( user=trans.user, stored_workflow=stored ).one()
            session.delete( association )
            session.flush()
            return self.list( trans )
        else:
            # Get session and workflow.
            stored = self.get_stored_workflow( trans, id )
            session.add( stored )

            # Do operation on workflow.
            if 'make_accessible_via_link' in kwargs:
                self._make_item_accessible( trans.sa_session, stored )
            elif 'make_accessible_and_publish' in kwargs:
                self._make_item_accessible( trans.sa_session, stored )
                stored.published = True
            elif 'publish' in kwargs:
                stored.published = True
            elif 'disable_link_access' in kwargs:
                stored.importable = False
            elif 'unpublish' in kwargs:
                stored.published = False
            elif 'disable_link_access_and_unpublish' in kwargs:
                stored.importable = stored.published = False
            elif 'unshare_user' in kwargs:
                user = session.query( model.User ).get( trans.security.decode_id( kwargs['unshare_user' ] ) )
                if not user:
                    error( "User not found for provided id" )
                association = session.query( model.StoredWorkflowUserShareAssociation ) \
                                     .filter_by( user=user, stored_workflow=stored ).one()
                session.delete( association )

            # Legacy issue: workflows made accessible before recent updates may not have a slug. Create slug for any workflows that need them.
            if stored.importable and not stored.slug:
                self._make_item_accessible( trans.sa_session, stored )

            session.flush()
            return trans.fill_template( "/workflow/sharing.mako", use_panels=True, item=stored )

    @web.expose
    @web.require_login( "to import a workflow", use_panels=True )
    def imp( self, trans, id, **kwargs ):
        """Imports a workflow shared by other users."""
        # Set referer message.
        referer = trans.request.referer
        if referer:
            referer_message = "<a href='%s'>return to the previous page</a>" % escape(referer)
        else:
            referer_message = "<a href='%s'>go to Galaxy's start page</a>" % url_for( '/' )

        # Do import.
        stored = self.get_stored_workflow( trans, id, check_ownership=False )
        if stored.importable is False:
            return trans.show_error_message( "The owner of this workflow has disabled imports via this link.<br>You can %s" % referer_message, use_panels=True )
        elif stored.deleted:
            return trans.show_error_message( "You can't import this workflow because it has been deleted.<br>You can %s" % referer_message, use_panels=True )
        self._import_shared_workflow( trans, stored )

        # Redirect to load galaxy frames.
        return trans.show_ok_message(
            message="""Workflow "%s" has been imported. <br>You can <a href="%s">start using this workflow</a> or %s."""
            % ( stored.name, web.url_for( controller='workflow' ), referer_message ), use_panels=True )

    @web.expose
    @web.require_login( "use Galaxy workflows" )
    def rename( self, trans, id, new_name=None, **kwargs ):
        stored = self.get_stored_workflow( trans, id )
        if new_name is not None:
            san_new_name = sanitize_html( new_name )
            stored.name = san_new_name
            stored.latest_workflow.name = san_new_name
            trans.sa_session.flush()
            trans.set_message( "Workflow renamed to '%s'." % san_new_name )
            return self.list( trans )
        else:
            return form( url_for(controller='workflow', action='rename', id=trans.security.encode_id(stored.id) ),
                         "Rename workflow",
                         submit_text="Rename",
                         use_panels=True
                         ).add_text( "new_name", "Workflow Name", value=to_unicode( stored.name ) )

    @web.expose
    @web.require_login( "use Galaxy workflows" )
    def rename_async( self, trans, id, new_name=None, **kwargs ):
        stored = self.get_stored_workflow( trans, id )
        if new_name:
            san_new_name = sanitize_html( new_name )
            stored.name = san_new_name
            stored.latest_workflow.name = san_new_name
            trans.sa_session.flush()
            return stored.name

    @web.expose
    @web.require_login( "use Galaxy workflows" )
    def annotate_async( self, trans, id, new_annotation=None, **kwargs ):
        stored = self.get_stored_workflow( trans, id )
        if new_annotation:
            # Sanitize annotation before adding it.
            new_annotation = sanitize_html( new_annotation, 'utf-8', 'text/html' )
            self.add_item_annotation( trans.sa_session, trans.get_user(), stored, new_annotation )
            trans.sa_session.flush()
            return new_annotation

    @web.expose
    @web.require_login( "rate items" )
    @web.json
    def rate_async( self, trans, id, rating ):
        """ Rate a workflow asynchronously and return updated community data. """

        stored = self.get_stored_workflow( trans, id, check_ownership=False, check_accessible=True )
        if not stored:
            return trans.show_error_message( "The specified workflow does not exist." )

        # Rate workflow.
        self.rate_item( trans.sa_session, trans.get_user(), stored, rating )

        return self.get_ave_item_rating_data( trans.sa_session, stored )

    @web.expose
    @web.require_login( "use Galaxy workflows" )
    def set_accessible_async( self, trans, id=None, accessible=False ):
        """ Set workflow's importable attribute and slug. """
        stored = self.get_stored_workflow( trans, id )

        # Only set if importable value would change; this prevents a change in the update_time unless attribute really changed.
        importable = accessible in ['True', 'true', 't', 'T']
        if stored and stored.importable != importable:
            if importable:
                self._make_item_accessible( trans.sa_session, stored )
            else:
                stored.importable = importable
            trans.sa_session.flush()
        return

    @web.expose
    def get_embed_html_async( self, trans, id ):
        """ Returns HTML for embedding a workflow in a page. """

        # TODO: user should be able to embed any item he has access to. see display_by_username_and_slug for security code.
        stored = self.get_stored_workflow( trans, id )
        if stored:
            return "Embedded Workflow '%s'" % stored.name

    @web.expose
    @web.json
    @web.require_login( "use Galaxy workflows" )
    def get_name_and_link_async( self, trans, id=None ):
        """ Returns workflow's name and link. """
        stored = self.get_stored_workflow( trans, id )

        return_dict = { "name": stored.name,
                        "link": url_for(controller='workflow',
                                        action="display_by_username_and_slug",
                                        username=stored.user.username,
                                        slug=stored.slug ) }
        return return_dict

    @web.expose
    @web.require_login( "use Galaxy workflows" )
    def gen_image( self, trans, id ):
        stored = self.get_stored_workflow( trans, id, check_ownership=True )
        try:
            svg = self._workflow_to_svg_canvas( trans, stored )
        except Exception:
            status = 'error'
            message = 'Galaxy is unable to create the SVG image. Please check your workflow, there might be missing tools.'
            return trans.fill_template( "/workflow/sharing.mako", use_panels=True, item=stored, status=status, message=message )
        trans.response.set_content_type("image/svg+xml")
        s = STANDALONE_SVG_TEMPLATE % svg.tostring()
        return s.encode('utf-8')

    @web.expose
    @web.require_login( "use Galaxy workflows" )
    def copy( self, trans, id, save_as_name=None ):
        # Get workflow to copy.
        stored = self.get_stored_workflow( trans, id, check_ownership=False )
        user = trans.get_user()
        if stored.user == user:
            owner = True
        else:
            if trans.sa_session.query( model.StoredWorkflowUserShareAssociation ) \
                    .filter_by( user=user, stored_workflow=stored ).count() == 0:
                error( "Workflow is not owned by or shared with current user" )
            owner = False

        # Copy.
        new_stored = model.StoredWorkflow()
        if (save_as_name):
            new_stored.name = '%s' % save_as_name
        else:
            new_stored.name = "Copy of '%s'" % stored.name
        new_stored.latest_workflow = stored.latest_workflow
        # Copy annotation.
        annotation_obj = self.get_item_annotation_obj( trans.sa_session, stored.user, stored )
        if annotation_obj:
            self.add_item_annotation( trans.sa_session, trans.get_user(), new_stored, annotation_obj.annotation )
        new_stored.copy_tags_from(trans.user, stored)
        if not owner:
            new_stored.name += " shared by '%s'" % stored.user.email
        new_stored.user = user
        # Persist
        session = trans.sa_session
        session.add( new_stored )
        session.flush()
        # Display the management page
        trans.set_message( 'Created new workflow with name "%s"' % escape( new_stored.name ) )
        return self.list( trans )

    @web.expose
    @web.require_login( "create workflows" )
    def create( self, trans, workflow_name=None, workflow_annotation="" ):
        """
        Create a new stored workflow with name `workflow_name`.
        """
        user = trans.get_user()
        if workflow_name is not None:
            # Create the new stored workflow
            stored_workflow = model.StoredWorkflow()
            stored_workflow.name = workflow_name
            stored_workflow.user = user
            self.create_item_slug( trans.sa_session, stored_workflow )
            # And the first (empty) workflow revision
            workflow = model.Workflow()
            workflow.name = workflow_name
            workflow.stored_workflow = stored_workflow
            stored_workflow.latest_workflow = workflow
            # Add annotation.
            workflow_annotation = sanitize_html( workflow_annotation, 'utf-8', 'text/html' )
            self.add_item_annotation( trans.sa_session, trans.get_user(), stored_workflow, workflow_annotation )
            # Persist
            session = trans.sa_session
            session.add( stored_workflow )
            session.flush()
            return self.editor( trans, id=trans.security.encode_id(stored_workflow.id ))
        else:
            return form( url_for(controller="workflow", action="create"), "Create New Workflow", submit_text="Create", use_panels=True ) \
                .add_text( "workflow_name", "Workflow Name", value="Unnamed workflow" ) \
                .add_text( "workflow_annotation",
                           "Workflow Annotation",
                           value="",
                           help="A description of the workflow; annotation is shown alongside shared or published workflows." )

    @web.json
    def save_workflow_as(self, trans, workflow_name, workflow_data, workflow_annotation=""):
        """
            Creates a new workflow based on Save As command. It is a new workflow, but
            is created with workflow_data already present.
        """
        user = trans.get_user()
        if workflow_name is not None:
            workflow_contents_manager = workflows.WorkflowContentsManager(trans.app)
            stored_workflow = model.StoredWorkflow()
            stored_workflow.name = workflow_name
            stored_workflow.user = user
            self.create_item_slug(trans.sa_session, stored_workflow)
            workflow = model.Workflow()
            workflow.name = workflow_name
            workflow.stored_workflow = stored_workflow
            stored_workflow.latest_workflow = workflow
            # Add annotation.
            workflow_annotation = sanitize_html( workflow_annotation, 'utf-8', 'text/html' )
            self.add_item_annotation( trans.sa_session, trans.get_user(), stored_workflow, workflow_annotation )

            # Persist
            session = trans.sa_session
            session.add( stored_workflow )
            session.flush()

            try:
                workflow, errors = workflow_contents_manager.update_workflow_from_dict(
                    trans,
                    stored_workflow,
                    workflow_data,
                )
            except workflows.MissingToolsException as e:
                return dict(
                    name=e.workflow.name,
                    message=("This workflow includes missing or invalid tools. "
                             "It cannot be saved until the following steps are removed or the missing tools are enabled."),
                    errors=e.errors,
                )
            return (trans.security.encode_id(stored_workflow.id))
        else:
            # This is an error state, 'save as' must have a workflow_name
            log.exception("Error in Save As workflow: no name.")

    @web.expose
    def delete( self, trans, id=None ):
        """
        Mark a workflow as deleted
        """
        # Load workflow from database
        stored = self.get_stored_workflow( trans, id )
        # Mark as deleted and save
        stored.deleted = True
        trans.user.stored_workflow_menu_entries = [entry for entry in trans.user.stored_workflow_menu_entries if entry.stored_workflow != stored]
        trans.sa_session.add( stored )
        trans.sa_session.flush()
        # Display the management page
        trans.set_message( "Workflow '%s' deleted" % escape( stored.name ) )
        return self.list( trans )

    @web.expose
    @web.require_login( "edit workflows" )
    def editor( self, trans, id=None ):
        """
        Render the main workflow editor interface. The canvas is embedded as
        an iframe (necessary for scrolling to work properly), which is
        rendered by `editor_canvas`.
        """
        if not id:
            error( "Invalid workflow id" )
        stored = self.get_stored_workflow( trans, id )
        workflows = trans.sa_session.query( model.StoredWorkflow ) \
            .filter_by( user=trans.user, deleted=False ) \
            .order_by( desc( model.StoredWorkflow.table.c.update_time ) ) \
            .all()
        return trans.fill_template( "workflow/editor.mako", workflows=workflows, stored=stored, annotation=self.get_item_annotation_str( trans.sa_session, trans.user, stored ) )

    @web.json
    def editor_form_post( self, trans, type=None, content_id=None, annotation=None, label=None, **incoming ):
        """
        Accepts a tool state and incoming values, and generates a new tool
        form and some additional information, packed into a json dictionary.
        This is used for the form shown in the right pane when a node
        is selected.
        """
        tool_state = incoming.pop( 'tool_state' )
        module = module_factory.from_dict( trans, {
            'type': type,
            'content_id': content_id,
            'tool_state': tool_state,
            'label': label or None
        } )
        module.update_state( incoming )
        return {
            'label': module.label,
            'tool_state': module.get_state(),
            'data_inputs': module.get_data_inputs(),
            'data_outputs': module.get_data_outputs(),
            'tool_errors': module.get_errors(),
            'form_html': module.get_config_form(),
            'annotation': annotation
        }

    @web.json
    def get_new_module_info( self, trans, type, **kwargs ):
        """
        Get the info for a new instance of a module initialized with default
        parameters (any keyword arguments will be passed along to the module).
        Result includes data inputs and outputs, html representation
        of the initial form, and the initial tool state (with default values).
        This is called asynchronously whenever a new node is added.
        """
        trans.workflow_building_mode = True
        module = module_factory.new( trans, type, **kwargs )
        tool_model = None
        return {
            'type': module.type,
            'name': module.get_name(),
            'content_id': module.get_content_id(),
            'tool_state': module.get_state(),
            'tool_model': tool_model,
            'tooltip': module.get_tooltip( static_path=url_for( '/static' ) ),
            'data_inputs': module.get_data_inputs(),
            'data_outputs': module.get_data_outputs(),
            'form_html': module.get_config_form(),
            'annotation': ""
        }

    @web.json
    def load_workflow( self, trans, id ):
        """
        Get the latest Workflow for the StoredWorkflow identified by `id` and
        encode it as a json string that can be read by the workflow editor
        web interface.
        """
        trans.workflow_building_mode = True
        stored = self.get_stored_workflow( trans, id, check_ownership=True, check_accessible=False )
        workflow_contents_manager = workflows.WorkflowContentsManager(trans.app)
        return workflow_contents_manager.workflow_to_dict( trans, stored, style="editor" )

    @web.json
    def save_workflow( self, trans, id, workflow_data ):
        """
        Save the workflow described by `workflow_data` with id `id`.
        """
        # Get the stored workflow
        stored = self.get_stored_workflow( trans, id )
        workflow_contents_manager = workflows.WorkflowContentsManager(trans.app)
        try:
            workflow, errors = workflow_contents_manager.update_workflow_from_dict(
                trans,
                stored,
                workflow_data,
            )
        except workflows.MissingToolsException as e:
            return dict(
                name=e.workflow.name,
                message="This workflow includes missing or invalid tools. "
                        "It cannot be saved until the following steps are removed or the missing tools are enabled.",
                errors=e.errors,
            )

        if workflow.has_errors:
            errors.append( "Some steps in this workflow have validation errors" )
        if workflow.has_cycles:
            errors.append( "This workflow contains cycles" )
        if errors:
            rval = dict( message="Workflow saved, but will not be runnable due to the following errors",
                         errors=errors )
        else:
            rval = dict( message="Workflow saved" )
        rval['name'] = workflow.name
        return rval

    @web.expose
    @web.require_login( "use workflows" )
    def export_to_myexp( self, trans, id, myexp_username, myexp_password ):
        """
        Exports a workflow to myExperiment website.
        """
        trans.workflow_building_mode = True
        stored = self.get_stored_workflow( trans, id, check_ownership=False, check_accessible=True )

        # Convert workflow to dict.
        workflow_dict = self._workflow_to_dict( trans, stored )

        #
        # Create and submit workflow myExperiment request.
        #

        # Create workflow content JSON.
        workflow_content = json.dumps( workflow_dict, indent=4, sort_keys=True )

        # Create myExperiment request.
        request_raw = trans.fill_template(
            "workflow/myexp_export.mako",
            workflow_name=workflow_dict['name'],
            workflow_description=workflow_dict['annotation'],
            workflow_content=workflow_content,
            workflow_svg=self._workflow_to_svg_canvas( trans, stored ).tostring()
        )
        # strip() b/c myExperiment XML parser doesn't allow white space before XML; utf-8 handles unicode characters.
        request = unicodify( request_raw.strip(), 'utf-8' )

        # Do request and get result.
        auth_header = base64.b64encode( '%s:%s' % ( myexp_username, myexp_password ))
        headers = { "Content-type": "text/xml", "Accept": "text/xml", "Authorization": "Basic %s" % auth_header }
        myexp_url = trans.app.config.get( "myexperiment_url", self.__myexp_url )
        conn = httplib.HTTPConnection( myexp_url )
        # NOTE: blocks web thread.
        conn.request("POST", "/workflow.xml", request, headers)
        response = conn.getresponse()
        response_data = response.read()
        conn.close()

        # Do simple parse of response to see if export successful and provide user feedback.
        parser = SingleTagContentsParser( 'id' )
        parser.feed( response_data )
        myexp_workflow_id = parser.tag_content
        workflow_list_str = " <br>Return to <a href='%s'>workflow list." % url_for( controller='workflow', action='list' )
        if myexp_workflow_id:
            return trans.show_message(
                """Workflow '%s' successfully exported to myExperiment. <br/>
                <a href="http://%s/workflows/%s">Click here to view the workflow on myExperiment</a> %s
                """ % ( stored.name, myexp_url, myexp_workflow_id, workflow_list_str ),
                use_panels=True )
        else:
            return trans.show_error_message(
                "Workflow '%s' could not be exported to myExperiment. Error: %s %s" %
                ( stored.name, response_data, workflow_list_str ), use_panels=True )

    @web.json_pretty
    def for_direct_import( self, trans, id ):
        """
        Get the latest Workflow for the StoredWorkflow identified by `id` and
        encode it as a json string that can be imported back into Galaxy

        This has slightly different information than the above. In particular,
        it does not attempt to decode forms and build UIs, it just stores
        the raw state.
        """
        stored = self.get_stored_workflow( trans, id, check_ownership=False, check_accessible=True )
        return self._workflow_to_dict( trans, stored )

    @web.json_pretty
    def export_to_file( self, trans, id ):
        """
        Get the latest Workflow for the StoredWorkflow identified by `id` and
        encode it as a json string that can be imported back into Galaxy

        This has slightly different information than the above. In particular,
        it does not attempt to decode forms and build UIs, it just stores
        the raw state.
        """

        # Get workflow.
        stored = self.get_stored_workflow( trans, id, check_ownership=False, check_accessible=True )

        # Stream workflow to file.
        stored_dict = self._workflow_to_dict( trans, stored )
        if not stored_dict:
            # This workflow has a tool that's missing from the distribution
            trans.response.status = 400
            return "Workflow cannot be exported due to missing tools."
        sname = stored.name
        sname = ''.join(c in FILENAME_VALID_CHARS and c or '_' for c in sname)[0:150]
        trans.response.headers["Content-Disposition"] = 'attachment; filename="Galaxy-Workflow-%s.ga"' % ( sname )
        trans.response.set_content_type( 'application/galaxy-archive' )
        return stored_dict

    @web.expose
    def import_workflow( self, trans, cntrller='workflow', **kwd ):
        """
        Import a workflow by reading an url, uploading a file, opening and reading the contents
        of a local file, or receiving the textual representation of a workflow via http.
        """
        url = kwd.get( 'url', '' )
        workflow_text = kwd.get( 'workflow_text', '' )
        message = str( escape( kwd.get( 'message', '' ) ) )
        status = kwd.get( 'status', 'done' )
        import_button = kwd.get( 'import_button', False )
        # The special Galaxy integration landing page's URL on myExperiment
        myexperiment_target_url = 'http://%s/galaxy?galaxy_url=%s' % \
            ( trans.app.config.get( "myexperiment_url", "www.myexperiment.org" ), url_for('/', qualified=True) )
        # The source of the workflow, used by myExperiment to indicate the workflow came from there.
        workflow_source = kwd.get( 'workflow_source', 'uploaded file' )
        # The following parameters will have values only if the workflow
        # id being imported from a Galaxy tool shed repository.
        tool_shed_url = kwd.get( 'tool_shed_url', '' )
        repository_metadata_id = kwd.get( 'repository_metadata_id', '' )
        add_to_menu = util.string_as_bool( kwd.get( 'add_to_menu', False ) )
        # The workflow_name parameter is in the request only if the import originated
        # from a Galaxy tool shed, in which case the value was encoded.
        workflow_name = kwd.get( 'workflow_name', '' )
        if workflow_name:
            workflow_name = encoding_util.tool_shed_decode( workflow_name )
        # The following parameters will have a value only if the import originated
        # from a tool shed repository installed locally or from the API.
        installed_repository_file = kwd.get( 'installed_repository_file', '' )
        repository_id = kwd.get( 'repository_id', '' )
        if installed_repository_file and not import_button:
            workflow_file = open( installed_repository_file, 'rb' )
            workflow_text = workflow_file.read()
            workflow_file.close()
            import_button = True
        if tool_shed_url and not import_button:
            # Use urllib (send another request to the tool shed) to retrieve the workflow.
            params = dict( repository_metadata_id=repository_metadata_id,
                           workflow_name=encoding_util.tool_shed_encode( workflow_name ),
                           open_for_url=True )
            pathspec = [ 'workflow', 'import_workflow' ]
            workflow_text = util.url_get( tool_shed_url, password_mgr=self.app.tool_shed_registry.url_auth( tool_shed_url ), pathspec=pathspec, params=params )
            import_button = True
        if import_button:
            workflow_data = None
            if url:
                # Load workflow from external URL
                # NOTE: blocks the web thread.
                try:
                    workflow_data = urllib2.urlopen( url ).read()
                except Exception as e:
                    message = "Failed to open URL: <b>%s</b><br>Exception: %s" % ( escape( url ), escape( str( e ) ) )
                    status = 'error'
            elif workflow_text:
                # This case occurs when the workflow_text was sent via http from the tool shed.
                workflow_data = workflow_text
            else:
                # Load workflow from browsed file.
                file_data = kwd.get( 'file_data', '' )
                if file_data in ( '', None ):
                    message = 'No exported Galaxy workflow files were selected.'
                    status = 'error'
                else:
                    uploaded_file = file_data.file
                    uploaded_file_name = uploaded_file.name
                    # uploaded_file_filename = file_data.filename
                    if os.path.getsize( os.path.abspath( uploaded_file_name ) ) > 0:
                        # We're reading the file as text so we can re-use the existing code below.
                        # This may not be ideal...
                        workflow_data = uploaded_file.read()
                    else:
                        message = 'You attempted to upload an empty file.'
                        status = 'error'
            if workflow_data:
                # Convert incoming workflow data from json
                try:
                    data = json.loads( workflow_data )
                except Exception as e:
                    data = None
                    message = "The data content does not appear to be a Galaxy workflow."
                    status = 'error'
                    log.exception("Error importing workflow.")
                if data:
                    # Create workflow if possible.  If a required tool is not available in the local
                    # Galaxy instance, the tool information will be available in the step_dict.
                    src = None
                    if cntrller != 'api':
                        src = workflow_source
                    workflow, missing_tool_tups = self._workflow_from_dict( trans, data, source=src, add_to_menu=add_to_menu )
                    workflow = workflow.latest_workflow
                    if workflow_name:
                        workflow.name = workflow_name
                    # Provide user feedback and show workflow list.
                    if workflow.has_errors:
                        message += "Imported, but some steps in this workflow have validation errors. "
                        status = "error"
                    if workflow.has_cycles:
                        message += "Imported, but this workflow contains cycles.  "
                        status = "error"
                    else:
                        message += "Workflow <b>%s</b> imported successfully.  " % escape( workflow.name )
                    if missing_tool_tups:
                        if trans.user_is_admin():
                            # A required tool is not available in the local Galaxy instance.
                            # TODO: It would sure be nice to be able to redirect to a mako template here that displays a nice
                            # page including the links to the configured tool sheds instead of this message, but trying
                            # to get the panels back is a nightmare since workflow eliminates the Galaxy panels.  Someone
                            # involved in workflow development needs to figure out what it will take to be able to switch
                            # back and forth between Galaxy (with panels ) and the workflow view (without panels ), having
                            # the Galaxy panels displayed whenever in Galaxy.
                            message += "The workflow requires the following tools that are not available in this Galaxy instance."
                            message += "You can likely install the required tools from one of the Galaxy tool sheds listed below.<br/>"
                            for missing_tool_tup in missing_tool_tups:
                                missing_tool_id, missing_tool_name, missing_tool_version, step_id = missing_tool_tup
                                message += "<b>Tool name</b> %s, <b>id</b> %s, <b>version</b> %s<br/>" % (
                                           escape( missing_tool_name ),
                                           escape( missing_tool_id ),
                                           escape( missing_tool_version ) )
                            message += "<br/>"
                            for shed_name, shed_url in trans.app.tool_shed_registry.tool_sheds.items():
                                if shed_url.endswith( '/' ):
                                    shed_url = shed_url.rstrip( '/' )
                                    url = '%s/repository/find_tools?galaxy_url=%s' % ( shed_url, url_for( '/', qualified=True ) )
                                    if missing_tool_tups:
                                        url += '&tool_id='
                                    for missing_tool_tup in missing_tool_tups:
                                        missing_tool_id = missing_tool_tup[0]
                                        url += '%s,' % escape( missing_tool_id )
                                message += '<a href="%s">%s</a><br/>' % ( url, shed_name )
                                status = 'error'
                            if installed_repository_file or tool_shed_url:
                                # Another Galaxy panels Hack: The request did not originate from the Galaxy
                                # workflow view, so we don't need to render the Galaxy panels.
                                action = 'center'
                            else:
                                # Another Galaxy panels hack: The request originated from the Galaxy
                                # workflow view, so we need to render the Galaxy panels.
                                action = 'index'
                            return trans.response.send_redirect( web.url_for( controller='admin',
                                                                              action=action,
                                                                              message=message,
                                                                              status=status ) )
                        else:
                            # TODO: Figure out what to do here...
                            pass
                    if tool_shed_url:
                        # We've received the textual representation of a workflow from a Galaxy tool shed.
                        message = "Workflow <b>%s</b> imported successfully." % escape( workflow.name )
                        url = '%s/workflow/view_workflow?repository_metadata_id=%s&workflow_name=%s&message=%s' % \
                            ( tool_shed_url, repository_metadata_id, encoding_util.tool_shed_encode( workflow_name ), message )
                        return trans.response.send_redirect( url )
                    elif installed_repository_file:
                        # The workflow was read from a file included with an installed tool shed repository.
                        message = "Workflow <b>%s</b> imported successfully." % escape( workflow.name )
                        if cntrller == 'api':
                            return status, message
                        return trans.response.send_redirect( web.url_for( controller='admin_toolshed',
                                                                          action='browse_repository',
                                                                          id=repository_id,
                                                                          message=message,
                                                                          status=status ) )
                    return self.list( trans )
        if cntrller == 'api':
            return status, message
        return trans.fill_template( "workflow/import.mako",
                                    url=url,
                                    message=message,
                                    status=status,
                                    use_panels=True,
                                    myexperiment_target_url=myexperiment_target_url )

    @web.expose
    def build_from_current_history( self, trans, job_ids=None, dataset_ids=None, dataset_collection_ids=None, workflow_name=None, dataset_names=None, dataset_collection_names=None ):
        user = trans.get_user()
        history = trans.get_history()
        if not user:
            return trans.show_error_message( "Must be logged in to create workflows" )
        if ( job_ids is None and dataset_ids is None ) or workflow_name is None:
            jobs, warnings = summarize( trans )
            # Render
            return trans.fill_template(
                "workflow/build_from_current_history.mako",
                jobs=jobs,
                warnings=warnings,
                history=history
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
                dataset_collection_names=dataset_collection_names
            )
            # Index page with message
            workflow_id = trans.security.encode_id( stored_workflow.id )
            return trans.show_message( 'Workflow "%s" created from current history. '
                                       'You can <a href="%s" target="_parent">edit</a> or <a href="%s">run</a> the workflow.'
                                       % ( escape( workflow_name ), url_for( controller='workflow', action='editor', id=workflow_id ),
                                           url_for( controller='workflow', action='run', id=workflow_id ) ) )

    @web.expose
    def run( self, trans, id, history_id=None, **kwargs ):
        history = None
        try:
            if history_id is not None:
                history_manager = histories.HistoryManager( trans.app )
                history = history_manager.get_owned( trans.security.decode_id( history_id ), trans.user, current_history=trans.history )
            else:
                history = trans.get_history()
            if history is None:
                raise exceptions.MessageException( 'History unavailable. Please specify a valid history id' )
        except Exception as e:
            raise exceptions.MessageException( '[history_id=%s] Failed to retrieve history. %s.' % ( history_id, str( e ) ) )
        trans.history = history
        workflow_manager = workflows.WorkflowsManager( trans.app )
        workflow_contents_manager = workflows.WorkflowContentsManager( trans.app )
        stored = workflow_manager.get_stored_accessible_workflow( trans, id )
        workflow_dict = workflow_contents_manager.workflow_to_dict( trans, stored, style='run' )
        return trans.fill_template( 'workflow/run.mako', workflow_dict=workflow_dict )

    def get_item( self, trans, id ):
        return self.get_stored_workflow( trans, id )

    @web.expose
    def tag_outputs( self, trans, id, **kwargs ):
        stored = self.get_stored_workflow( trans, id, check_ownership=False )
        user = trans.get_user()
        if stored.user != user:
            if trans.sa_session.query( model.StoredWorkflowUserShareAssociation ) \
                    .filter_by( user=user, stored_workflow=stored ).count() == 0:
                error( "Workflow is not owned by or shared with current user" )
        # Get the latest revision
        workflow = stored.latest_workflow
        # It is possible for a workflow to have 0 steps
        if len( workflow.steps ) == 0:
            error( "Workflow cannot be tagged for outputs because it does not have any steps" )
        if workflow.has_cycles:
            error( "Workflow cannot be tagged for outputs because it contains cycles" )
        if workflow.has_errors:
            error( "Workflow cannot be tagged for outputs because of validation errors in some steps" )
        # Build the state for each step
        errors = {}
        has_upgrade_messages = False
        # has_errors is never used
        # has_errors = False
        if kwargs:
            # If kwargs were provided, the states for each step should have
            # been POSTed
            for step in workflow.steps:
                if step.type == 'tool':
                    # Extract just the output flags for this step.
                    p = "%s|otag|" % step.id
                    l = len(p)
                    outputs = [k[l:] for ( k, v ) in kwargs.iteritems() if k.startswith( p )]
                    if step.workflow_outputs:
                        for existing_output in step.workflow_outputs:
                            if existing_output.output_name not in outputs:
                                trans.sa_session.delete(existing_output)
                            else:
                                outputs.remove(existing_output.output_name)
                    for outputname in outputs:
                        m = model.WorkflowOutput(workflow_step_id=int(step.id), output_name=outputname)
                        trans.sa_session.add(m)
        # Prepare each step
        trans.sa_session.flush()
        module_injector = WorkflowModuleInjector( trans )
        for step in workflow.steps:
            step.upgrade_messages = {}
            # Contruct modules
            module_injector.inject( step )
            if step.upgrade_messages:
                has_upgrade_messages = True
            if step.type == 'tool' or step.type is None:
                # Error dict
                if step.tool_errors:
                    errors[step.id] = step.tool_errors
        # Render the form
        return trans.fill_template(
            "workflow/tag_outputs.mako",
            steps=workflow.steps,
            workflow=stored,
            has_upgrade_messages=has_upgrade_messages,
            errors=errors,
            incoming=kwargs
        )

    @web.expose
    def configure_menu( self, trans, workflow_ids=None ):
        user = trans.get_user()
        if trans.request.method == "POST":
            if workflow_ids is None:
                workflow_ids = []
            elif type( workflow_ids ) != list:
                workflow_ids = [ workflow_ids ]
            sess = trans.sa_session
            # This explicit remove seems like a hack, need to figure out
            # how to make the association do it automatically.
            for m in user.stored_workflow_menu_entries:
                sess.delete( m )
            user.stored_workflow_menu_entries = []
            q = sess.query( model.StoredWorkflow )
            # To ensure id list is unique
            seen_workflow_ids = set()
            for id in workflow_ids:
                if id in seen_workflow_ids:
                    continue
                else:
                    seen_workflow_ids.add( id )
                m = model.StoredWorkflowMenuEntry()
                m.stored_workflow = q.get( id )
                user.stored_workflow_menu_entries.append( m )
            sess.flush()
            message = "Menu updated"
            refresh_frames = ['tools']
        else:
            message = None
            refresh_frames = []
        user = trans.get_user()
        ids_in_menu = set( [ x.stored_workflow_id for x in user.stored_workflow_menu_entries ] )
        workflows = trans.sa_session.query( model.StoredWorkflow ) \
            .filter_by( user=user, deleted=False ) \
            .order_by( desc( model.StoredWorkflow.table.c.update_time ) ) \
            .all()
        shared_by_others = trans.sa_session \
            .query( model.StoredWorkflowUserShareAssociation ) \
            .filter_by( user=user ) \
            .filter( model.StoredWorkflow.deleted == expression.false() ) \
            .all()
        return trans.fill_template( "workflow/configure_menu.mako",
                                    workflows=workflows,
                                    shared_by_others=shared_by_others,
                                    ids_in_menu=ids_in_menu,
                                    message=message,
                                    refresh_frames=refresh_frames )

    def _workflow_to_svg_canvas( self, trans, stored ):
        workflow = stored.latest_workflow
        workflow_canvas = WorkflowCanvas()
        for step in workflow.steps:
            # Load from database representation
            module = module_factory.from_workflow_step( trans, step )
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


def _build_workflow_on_str(instance_ds_names):
    # Returns suffix for new histories based on multi input iteration
    num_multi_inputs = len(instance_ds_names)
    if num_multi_inputs == 0:
        return ""
    elif num_multi_inputs == 1:
        return " on %s" % instance_ds_names[0]
    else:
        return " on %s and %s" % (", ".join(instance_ds_names[0:-1]), instance_ds_names[-1])


def _expand_multiple_inputs(kwargs):
    (single_inputs, matched_multi_inputs, multiplied_multi_inputs) = _split_inputs(kwargs)

    # Build up every combination of inputs to be run together.
    input_combos = _extend_with_matched_combos(single_inputs, matched_multi_inputs)
    input_combos = _extend_with_multiplied_combos(input_combos, multiplied_multi_inputs)

    # Input name that are multiply specified
    multi_input_keys = matched_multi_inputs.keys() + multiplied_multi_inputs.keys()

    for input_combo in input_combos:
        for key, value in input_combo.iteritems():
            kwargs[key] = value
        yield (kwargs, multi_input_keys)


def _extend_with_matched_combos(single_inputs, multi_inputs):
    if len(multi_inputs) == 0:
        return [single_inputs]

    matched_multi_inputs = []

    first_multi_input_key = multi_inputs.keys()[0]
    first_multi_value = multi_inputs.get(first_multi_input_key)

    for value in first_multi_value:
        new_inputs = _copy_and_extend_inputs(single_inputs, first_multi_input_key, value)
        matched_multi_inputs.append(new_inputs)

    for multi_input_key, multi_input_values in multi_inputs.iteritems():
        if multi_input_key == first_multi_input_key:
            continue
        if len(multi_input_values) != len(first_multi_value):
            raise Exception("Failed to match up multi-select inputs, must select equal number of data files in each multiselect")
        for index, value in enumerate(multi_input_values):
            matched_multi_inputs[index][multi_input_key] = value
    return matched_multi_inputs


def _extend_with_multiplied_combos(input_combos, multi_inputs):
    combos = input_combos

    for multi_input_key, multi_input_value in multi_inputs.iteritems():
        iter_combos = []

        for combo in combos:
            for input_value in multi_input_value:
                iter_combos.append(_copy_and_extend_inputs(combo, multi_input_key, input_value))

        combos = iter_combos
    return combos


def _copy_and_extend_inputs(inputs, key, value):
    new_inputs = dict(inputs)
    new_inputs[key] = value
    return new_inputs


def _split_inputs(kwargs):
    """
    """
    input_keys = filter(lambda a: a.endswith('|input'), kwargs)
    single_inputs = {}
    matched_multi_inputs = {}
    multiplied_multi_inputs = {}
    for input_key in input_keys:
        input_val = kwargs[input_key]
        if isinstance(input_val, list):
            input_base = input_key[:-len("|input")]
            mode_key = "%s|multi_mode" % input_base
            mode = kwargs.get(mode_key, "matched")
            if mode == "matched":
                matched_multi_inputs[input_key] = input_val
            else:
                multiplied_multi_inputs[input_key] = input_val
        else:
            single_inputs[input_key] = input_val
    return (single_inputs, matched_multi_inputs, multiplied_multi_inputs)
