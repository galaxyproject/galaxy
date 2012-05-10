from galaxy.web.base.controller import *

import pkg_resources
pkg_resources.require( "simplejson" )
pkg_resources.require( "SVGFig" )
import simplejson
import base64, httplib, urllib2, sgmllib, svgfig, urllib, urllib2
import math
from galaxy.web.framework.helpers import time_ago, grids
from galaxy.tools.parameters import *
from galaxy.tools import DefaultToolState
from galaxy.tools.parameters.grouping import Repeat, Conditional
from galaxy.datatypes.data import Data
from galaxy.util.odict import odict
from galaxy.util.sanitize_html import sanitize_html
from galaxy.util.topsort import topsort, topsort_levels, CycleError
from galaxy.workflow.modules import *
from galaxy import model
from galaxy import util
from galaxy.model.mapping import desc
from galaxy.model.orm import *
from galaxy.model.item_attrs import *
from galaxy.web.framework.helpers import to_unicode
from galaxy.jobs.actions.post import ActionBox

class StoredWorkflowListGrid( grids.Grid ):
    class StepsColumn( grids.GridColumn ):
        def get_value(self, trans, grid, workflow):
            return len( workflow.latest_workflow.steps )

    # Grid definition
    use_panels = True
    title = "Saved Workflows"
    model_class = model.StoredWorkflow
    default_filter = { "name" : "All", "tags": "All" }
    default_sort_key = "-update_time"
    columns = [
        grids.TextColumn( "Name", key="name", attach_popup=True, filterable="advanced" ),
        grids.IndividualTagsColumn( "Tags", "tags", model_tag_association_class=model.StoredWorkflowTagAssociation, filterable="advanced", grid_name="StoredWorkflowListGrid" ),
        StepsColumn( "Steps" ),
        grids.GridColumn( "Created", key="create_time", format=time_ago ),
        grids.GridColumn( "Last Updated", key="update_time", format=time_ago ),
    ]
    columns.append(
        grids.MulticolFilterColumn(
        "Search",
        cols_to_filter=[ columns[0], columns[1] ],
        key="free-text-search", visible=False, filterable="standard" )
                )
    operations = [
        grids.GridOperation( "Edit", allow_multiple=False, condition=( lambda item: not item.deleted ), async_compatible=False ),
        grids.GridOperation( "Run", condition=( lambda item: not item.deleted ), async_compatible=False ),
        grids.GridOperation( "Clone", condition=( lambda item: not item.deleted ), async_compatible=False  ),
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
        grids.PublicURLColumn( "Name", key="name", filterable="advanced" ),
        grids.OwnerAnnotationColumn( "Annotation", key="annotation", model_annotation_association_class=model.StoredWorkflowAnnotationAssociation, filterable="advanced" ),
        grids.OwnerColumn( "Owner", key="username", model_class=model.User, filterable="advanced" ),
        grids.CommunityRatingColumn( "Community Rating", key="rating" ),
        grids.CommunityTagsColumn( "Community Tags", key="tags", model_tag_association_class=model.StoredWorkflowTagAssociation, filterable="advanced", grid_name="PublicWorkflowListGrid" ),
        grids.ReverseSortColumn( "Last Updated", key="update_time", format=time_ago )
    ]
    columns.append(
        grids.MulticolFilterColumn(
        "Search name, annotation, owner, and tags",
        cols_to_filter=[ columns[0], columns[1], columns[2], columns[4] ],
        key="free-text-search", visible=False, filterable="standard" )
                )
    operations = []
    def build_initial_query( self, trans, **kwargs ):
        # Join so that searching stored_workflow.user makes sense.
        return trans.sa_session.query( self.model_class ).join( model.User.table )
    def apply_query_filter( self, trans, query, **kwargs ):
        # A public workflow is published, has a slug, and is not deleted.
        return query.filter( self.model_class.published==True ).filter( self.model_class.slug != None ).filter( self.model_class.deleted == False )

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

class WorkflowController( BaseUIController, Sharable, UsesStoredWorkflow, UsesAnnotations, UsesItemRatings ):
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
        status = message = None
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
            .filter( model.StoredWorkflow.deleted == False ) \
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
                                    workflows = workflows,
                                    shared_by_others = shared_by_others )

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
            .filter( model.StoredWorkflow.deleted == False ) \
            .order_by( desc( model.StoredWorkflow.table.c.update_time ) ) \
            .all()
        return trans.fill_template( "workflow/list_for_run.mako",
                                    workflows = workflows,
                                    shared_by_others = shared_by_others )

    @web.expose
    def list_published( self, trans, **kwargs ):
        grid = self.published_list_grid( trans, **kwargs )
        if 'async' in kwargs:
            return grid
        else:
            # Render grid wrapped in panels
            return trans.fill_template( "workflow/list_published.mako", grid=grid )

    @web.expose
    def display_by_username_and_slug( self, trans, username, slug ):
        """ Display workflow based on a username and slug. """

        # Get workflow.
        session = trans.sa_session
        user = session.query( model.User ).filter_by( username=username ).first()
        stored_workflow = trans.sa_session.query( model.StoredWorkflow ).filter_by( user=user, slug=slug, deleted=False ).first()
        return self.display(trans, stored_workflow)

    @web.expose
    def display_by_id( self, trans, id ):
        """ Display workflow based on id. """
        # Get workflow.
        stored_workflow = self.get_stored_workflow( trans, id )
        return self.display(trans, stored_workflow)

    def display(self, trans, stored_workflow):
        """ Base workflow display """
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
                                            user_item_rating = user_item_rating, ave_item_rating=ave_item_rating, num_ratings=num_ratings )

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
        return trans.stream_template_mako( "/workflow/item_content.mako", item = stored, item_data = stored.latest_workflow.steps )

    @web.expose
    @web.require_login( "use Galaxy workflows" )
    def share( self, trans, id, email="", use_panels=False ):
        msg = mtype = None
        # Load workflow from database
        stored = self.get_stored_workflow( trans, id )
        if email:
            other = trans.sa_session.query( model.User ) \
                                    .filter( and_( model.User.table.c.email==email,
                                                   model.User.table.c.deleted==False ) ) \
                                    .first()
            if not other:
                mtype = "error"
                msg = ( "User '%s' does not exist" % email )
            elif other == trans.get_user():
                mtype = "error"
                msg = ( "You cannot share a workflow with yourself" )
            elif trans.sa_session.query( model.StoredWorkflowUserShareAssociation ) \
                    .filter_by( user=other, stored_workflow=stored ).count() > 0:
                mtype = "error"
                msg = ( "Workflow already shared with '%s'" % email )
            else:
                share = model.StoredWorkflowUserShareAssociation()
                share.stored_workflow = stored
                share.user = other
                session = trans.sa_session
                session.add( share )
                self.create_item_slug( session, stored )
                session.flush()
                trans.set_message( "Workflow '%s' shared with user '%s'" % ( stored.name, other.email ) )
                return trans.response.send_redirect( url_for( controller='workflow', action='sharing', id=id ) )
        return trans.fill_template( "/ind_share_base.mako",
                                    message = msg,
                                    messagetype = mtype,
                                    item=stored,
                                    email=email,
                                    use_panels=use_panels )

    @web.expose
    @web.require_login( "use Galaxy workflows" )
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
        # Set referer message.
        referer = trans.request.referer
        if referer is not "":
            referer_message = "<a href='%s'>return to the previous page</a>" % referer
        else:
            referer_message = "<a href='%s'>go to Galaxy's start page</a>" % url_for( '/' )

        # Do import.
        session = trans.sa_session
        stored = self.get_stored_workflow( trans, id, check_ownership=False )
        if stored.importable == False:
            return trans.show_error_message( "The owner of this workflow has disabled imports via this link.<br>You can %s" % referer_message, use_panels=True )
        elif stored.deleted:
            return trans.show_error_message( "You can't import this workflow because it has been deleted.<br>You can %s" % referer_message, use_panels=True )
        else:
            # Copy workflow.
            imported_stored = model.StoredWorkflow()
            imported_stored.name = "imported: " + stored.name
            imported_stored.latest_workflow = stored.latest_workflow
            imported_stored.user = trans.user
            # Save new workflow.
            session = trans.sa_session
            session.add( imported_stored )
            session.flush()

            # Copy annotations.
            self.copy_item_annotation( session, stored.user, stored, imported_stored.user, imported_stored )
            for order_index, step in enumerate( stored.latest_workflow.steps ):
                self.copy_item_annotation( session, stored.user, step, \
                                            imported_stored.user, imported_stored.latest_workflow.steps[order_index] )
            session.flush()

            # Redirect to load galaxy frames.
            return trans.show_ok_message(
                message="""Workflow "%s" has been imported. <br>You can <a href="%s">start using this workflow</a> or %s."""
                % ( stored.name, web.url_for( controller='workflow' ), referer_message ), use_panels=True )

    @web.expose
    @web.require_login( "use Galaxy workflows" )
    def edit_attributes( self, trans, id, **kwargs ):
        # Get workflow and do error checking.
        stored = self.get_stored_workflow( trans, id )
        if not stored:
            error( "You do not own this workflow or workflow ID is invalid." )
        # Update workflow attributes if new values submitted.
        if 'name' in kwargs:
            # Rename workflow.
            stored.name = sanitize_html( kwargs['name'] )
        if 'annotation' in kwargs:
            # Set workflow annotation; sanitize annotation before adding it.
            annotation = sanitize_html( kwargs[ 'annotation' ], 'utf-8', 'text/html' )
            self.add_item_annotation( trans.sa_session, trans.get_user(), stored,  annotation )
        trans.sa_session.flush()
        return trans.fill_template( 'workflow/edit_attributes.mako',
                                    stored=stored,
                                    annotation=self.get_item_annotation_str( trans.sa_session, trans.user, stored )
                                    )

    @web.expose
    @web.require_login( "use Galaxy workflows" )
    def rename( self, trans, id, new_name=None, **kwargs ):
        stored = self.get_stored_workflow( trans, id )
        if new_name is not None:
            san_new_name = sanitize_html( new_name )
            stored.name = san_new_name
            stored.latest_workflow.name = san_new_name
            trans.sa_session.flush()
            # For current workflows grid:
            trans.set_message ( "Workflow renamed to '%s'." % new_name )
            return self.list( trans )
            # For new workflows grid:
            #message = "Workflow renamed to '%s'." % new_name
            #return self.list_grid( trans, message=message, status='done' )
        else:
            return form( url_for( action='rename', id=trans.security.encode_id(stored.id) ),
                         "Rename workflow", submit_text="Rename", use_panels=True ) \
                .add_text( "new_name", "Workflow Name", value=to_unicode( stored.name ) )

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
        stored_rating = self.rate_item( trans.sa_session, trans.get_user(), stored, rating )

        return self.get_ave_item_rating_data( trans.sa_session, stored )

    @web.expose
    @web.require_login( "use Galaxy workflows" )
    def set_accessible_async( self, trans, id=None, accessible=False ):
        """ Set workflow's importable attribute and slug. """
        stored = self.get_stored_workflow( trans, id )

        # Only set if importable value would change; this prevents a change in the update_time unless attribute really changed.
        importable = accessible in ['True', 'true', 't', 'T'];
        if stored and stored.importable != importable:
            if importable:
                self._make_item_accessible( trans.sa_session, stored )
            else:
                stored.importable = importable
            trans.sa_session.flush()
        return

    @web.expose
    @web.require_login( "modify Galaxy items" )
    def set_slug_async( self, trans, id, new_slug ):
        stored = self.get_stored_workflow( trans, id )
        if stored:
            stored.slug = new_slug
            trans.sa_session.flush()
            return stored.slug

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

        if self.create_item_slug( trans.sa_session, stored ):
            trans.sa_session.flush()
        return_dict = { "name" : stored.name, "link" : url_for( action="display_by_username_and_slug", username=stored.user.username, slug=stored.slug ) }
        return return_dict

    @web.expose
    @web.require_login( "use Galaxy workflows" )
    def gen_image( self, trans, id ):
        stored = self.get_stored_workflow( trans, id, check_ownership=True )
        session = trans.sa_session

        workflow = stored.latest_workflow
        data = []

        canvas = svgfig.canvas(style="stroke:black; fill:none; stroke-width:1px; stroke-linejoin:round; text-anchor:left")
        text = svgfig.SVG("g")
        connectors = svgfig.SVG("g")
        boxes = svgfig.SVG("g")
        svgfig.Text.defaults["font-size"] = "10px"

        in_pos = {}
        out_pos = {}
        margin = 5
        line_px = 16 # how much spacing between input/outputs
        widths = {} # store px width for boxes of each step
        max_width, max_x, max_y = 0, 0, 0

        for step in workflow.steps:
            # Load from database representation
            module = module_factory.from_workflow_step( trans, step )

            # Pack attributes into plain dictionary
            step_dict = {
                'id': step.order_index,
                'data_inputs': module.get_data_inputs(),
                'data_outputs': module.get_data_outputs(),
                'position': step.position
            }

            input_conn_dict = {}
            for conn in step.input_connections:
                input_conn_dict[ conn.input_name ] = \
                    dict( id=conn.output_step.order_index, output_name=conn.output_name )
            step_dict['input_connections'] = input_conn_dict

            data.append(step_dict)

            x, y = step.position['left'], step.position['top']
            count = 0

            max_len = len(module.get_name()) * 1.5
            text.append( svgfig.Text(x, y + 20, module.get_name(), **{"font-size": "14px"} ).SVG() )

            y += 45
            for di in module.get_data_inputs():
                cur_y = y+count*line_px
                if step.order_index not in in_pos:
                    in_pos[step.order_index] = {}
                in_pos[step.order_index][di['name']] = (x, cur_y)
                text.append( svgfig.Text(x, cur_y, di['label']).SVG() )
                count += 1
                max_len = max(max_len, len(di['label']))


            if len(module.get_data_inputs()) > 0:
                y += 15

            for do in module.get_data_outputs():
                cur_y = y+count*line_px
                if step.order_index not in out_pos:
                    out_pos[step.order_index] = {}
                out_pos[step.order_index][do['name']] = (x, cur_y)
                text.append( svgfig.Text(x, cur_y, do['name']).SVG() )
                count += 1
                max_len = max(max_len, len(do['name']))

            widths[step.order_index] = max_len*5.5
            max_x = max(max_x, step.position['left'])
            max_y = max(max_y, step.position['top'])
            max_width = max(max_width, widths[step.order_index])

        for step_dict in data:
            width = widths[step_dict['id']]
            x, y = step_dict['position']['left'], step_dict['position']['top']
            boxes.append( svgfig.Rect(x-margin, y, x+width-margin, y+30, fill="#EBD9B2").SVG() )
            box_height = (len(step_dict['data_inputs']) + len(step_dict['data_outputs'])) * line_px + margin

            # Draw separator line
            if len(step_dict['data_inputs']) > 0:
                box_height += 15
                sep_y = y + len(step_dict['data_inputs']) * line_px + 40
                text.append( svgfig.Line(x-margin, sep_y, x+width-margin, sep_y).SVG() ) #

            # input/output box
            boxes.append( svgfig.Rect(x-margin, y+30, x+width-margin, y+30+box_height, fill="#ffffff").SVG() )

            for conn, output_dict in step_dict['input_connections'].iteritems():
                in_coords = in_pos[step_dict['id']][conn]
                out_conn_pos = out_pos[output_dict['id']][output_dict['output_name']]
                adjusted = (out_conn_pos[0] + widths[output_dict['id']], out_conn_pos[1])
                text.append( svgfig.SVG("circle", cx=out_conn_pos[0]+widths[output_dict['id']]-margin, cy=out_conn_pos[1]-margin, r=5, fill="#ffffff" ) )
                connectors.append( svgfig.Line(adjusted[0], adjusted[1]-margin, in_coords[0]-10, in_coords[1], arrow_end="true" ).SVG() )

        canvas.append(connectors)
        canvas.append(boxes)
        canvas.append(text)
        width, height = (max_x + max_width + 50), max_y + 300
        canvas['width'] = "%s px" % width
        canvas['height'] = "%s px" % height
        canvas['viewBox'] = "0 0 %s %s" % (width, height)
        trans.response.set_content_type("image/svg+xml")
        return canvas.standalone_xml()


    @web.expose
    @web.require_login( "use Galaxy workflows" )
    def clone( self, trans, id ):
        # Get workflow to clone.
        stored = self.get_stored_workflow( trans, id, check_ownership=False )
        user = trans.get_user()
        if stored.user == user:
            owner = True
        else:
            if trans.sa_session.query( model.StoredWorkflowUserShareAssociation ) \
                    .filter_by( user=user, stored_workflow=stored ).count() == 0:
                error( "Workflow is not owned by or shared with current user" )
            owner = False

        # Clone.
        new_stored = model.StoredWorkflow()
        new_stored.name = "Clone of '%s'" % stored.name
        new_stored.latest_workflow = stored.latest_workflow
        # Clone annotation.
        annotation_obj = self.get_item_annotation_obj( trans.sa_session, stored.user, stored )
        if annotation_obj:
            self.add_item_annotation( trans.sa_session, trans.get_user(), new_stored, annotation_obj.annotation )
        # Clone tags.
        for swta in stored.owner_tags:
            new_swta = model.StoredWorkflowTagAssociation()
            new_swta.tag = swta.tag
            new_swta.user = trans.user
            new_swta.user_tname = swta.user_tname
            new_swta.user_value = swta.user_value
            new_swta.value = swta.value
            new_stored.tags.append( new_swta )
        if not owner:
            new_stored.name += " shared by '%s'" % stored.user.email
        new_stored.user = user
        # Persist
        session = trans.sa_session
        session.add( new_stored )
        session.flush()
        # Display the management page
        trans.set_message( 'Clone created with name "%s"' % new_stored.name )
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
            # Display the management page
            trans.set_message( "Workflow '%s' created" % stored_workflow.name )
            return self.list( trans )
        else:
            return form( url_for(), "Create New Workflow", submit_text="Create", use_panels=True ) \
                    .add_text( "workflow_name", "Workflow Name", value="Unnamed workflow" ) \
                    .add_text( "workflow_annotation", "Workflow Annotation", value="", help="A description of the workflow; annotation is shown alongside shared or published workflows." )

    @web.expose
    def delete( self, trans, id=None ):
        """
        Mark a workflow as deleted
        """
        # Load workflow from database
        stored = self.get_stored_workflow( trans, id )
        # Marke as deleted and save
        stored.deleted = True
        trans.sa_session.add( stored )
        trans.sa_session.flush()
        # Display the management page
        trans.set_message( "Workflow '%s' deleted" % stored.name )
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
        return trans.fill_template( "workflow/editor.mako", stored=stored, annotation=self.get_item_annotation_str( trans.sa_session, trans.user, stored ) )

    @web.json
    def editor_form_post( self, trans, type='tool', tool_id=None, annotation=None, **incoming ):
        """
        Accepts a tool state and incoming values, and generates a new tool
        form and some additional information, packed into a json dictionary.
        This is used for the form shown in the right pane when a node
        is selected.
        """

        trans.workflow_building_mode = True
        module = module_factory.from_dict( trans, {
            'type': type,
            'tool_id': tool_id,
            'tool_state': incoming.pop("tool_state")
        } )
        module.update_state( incoming )

        if type=='tool':
            return {
                'tool_state': module.get_state(),
                'data_inputs': module.get_data_inputs(),
                'data_outputs': module.get_data_outputs(),
                'tool_errors': module.get_errors(),
                'form_html': module.get_config_form(),
                'annotation': annotation,
                'post_job_actions': module.get_post_job_actions()
            }
        else:
            return {
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
        return {
            'type': module.type,
            'name':  module.get_name(),
            'tool_id': module.get_tool_id(),
            'tool_state': module.get_state(),
            'tooltip': module.get_tooltip(),
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
        user = trans.get_user()
        id = trans.security.decode_id( id )
        trans.workflow_building_mode = True
        # Load encoded workflow from database
        stored = trans.sa_session.query( model.StoredWorkflow ).get( id )
        assert stored.user == user
        workflow = stored.latest_workflow
        # Pack workflow data into a dictionary and return
        data = {}
        data['name'] = workflow.name
        data['steps'] = {}
        data['upgrade_messages'] = {}
        # For each step, rebuild the form and encode the state
        for step in workflow.steps:
            # Load from database representation
            module = module_factory.from_workflow_step( trans, step )
            if not module:
                step_annotation = self.get_item_annotation_obj( trans.sa_session, trans.user, step )
                annotation_str = ""
                if step_annotation:
                    annotation_str = step_annotation.annotation
                invalid_tool_form_html = """<div class="toolForm tool-node-error"><div class="toolFormTitle form-row-error">Unrecognized Tool: %s</div><div class="toolFormBody"><div class="form-row">
                                            The tool id '%s' for this tool is unrecognized.<br/><br/>To save this workflow, you will need to delete this step or enable the tool.
                                            </div></div></div>""" % (step.tool_id, step.tool_id)
                step_dict = {
                    'id': step.order_index,
                    'type': 'invalid',
                    'tool_id': step.tool_id,
                    'name': 'Unrecognized Tool: %s' % step.tool_id,
                    'tool_state': None,
                    'tooltip': None,
                    'tool_errors': ["Unrecognized Tool Id: %s" % step.tool_id],
                    'data_inputs': [],
                    'data_outputs': [],
                    'form_html': invalid_tool_form_html,
                    'annotation' : annotation_str,
                    'input_connections' : {},
                    'post_job_actions' : {},
                    'workflow_outputs' : []
                }
                # Position
                step_dict['position'] = step.position
                # Add to return value
                data['steps'][step.order_index] = step_dict
                continue
            # Fix any missing parameters
            upgrade_message = module.check_and_update_state()
            if upgrade_message:
                # FIXME: Frontend should be able to handle workflow messages
                #        as a dictionary not just the values
                data['upgrade_messages'][step.order_index] = upgrade_message.values()
            # Get user annotation.
            step_annotation = self.get_item_annotation_obj( trans.sa_session, trans.user, step )
            annotation_str = ""
            if step_annotation:
                annotation_str = step_annotation.annotation
            # Pack attributes into plain dictionary
            step_dict = {
                'id': step.order_index,
                'type': module.type,
                'tool_id': module.get_tool_id(),
                'name': module.get_name(),
                'tool_state': module.get_state(),
                'tooltip': module.get_tooltip(),
                'tool_errors': module.get_errors(),
                'data_inputs': module.get_data_inputs(),
                'data_outputs': module.get_data_outputs(),
                'form_html': module.get_config_form(),
                'annotation' : annotation_str,
                'post_job_actions' : {},
                'workflow_outputs' : []
            }
            # Connections
            input_connections = step.input_connections
            if step.type is None or step.type == 'tool':
                # Determine full (prefixed) names of valid input datasets
                data_input_names = {}
                def callback( input, value, prefixed_name, prefixed_label ):
                    if isinstance( input, DataToolParameter ):
                        data_input_names[ prefixed_name ] = True
                visit_input_values( module.tool.inputs, module.state.inputs, callback )
                # Filter
                # FIXME: this removes connection without displaying a message currently!
                input_connections = [ conn for conn in input_connections if conn.input_name in data_input_names ]
                # post_job_actions
                pja_dict = {}
                for pja in step.post_job_actions:
                    pja_dict[pja.action_type+pja.output_name] = dict(action_type = pja.action_type,
                                            output_name = pja.output_name,
                                            action_arguments = pja.action_arguments)
                step_dict['post_job_actions'] = pja_dict
                #workflow outputs
                outputs = []
                for output in step.workflow_outputs:
                    outputs.append(output.output_name)
                step_dict['workflow_outputs'] = outputs
            # Encode input connections as dictionary
            input_conn_dict = {}
            for conn in input_connections:
                input_conn_dict[ conn.input_name ] = \
                    dict( id=conn.output_step.order_index, output_name=conn.output_name )
            step_dict['input_connections'] = input_conn_dict
            # Position
            step_dict['position'] = step.position
            # Add to return value
            data['steps'][step.order_index] = step_dict
        return data

    @web.json
    def save_workflow( self, trans, id, workflow_data ):
        """
        Save the workflow described by `workflow_data` with id `id`.
        """
        # Get the stored workflow
        stored = self.get_stored_workflow( trans, id )
        # Put parameters in workflow mode
        trans.workflow_building_mode = True
        # Convert incoming workflow data from json
        data = simplejson.loads( workflow_data )
        # Create new workflow from incoming data
        workflow = model.Workflow()
        # Just keep the last name (user can rename later)
        workflow.name = stored.name
        # Assume no errors until we find a step that has some
        workflow.has_errors = False
        # Create each step
        steps = []
        # The editor will provide ids for each step that we don't need to save,
        # but do need to use to make connections
        steps_by_external_id = {}
        errors = []
        for key, step_dict in data['steps'].iteritems():
            if step_dict['type'] != 'data_input' and step_dict['tool_id'] not in trans.app.toolbox.tools_by_id:
                errors.append("Step %s requires tool '%s'." % (step_dict['id'], step_dict['tool_id']))
        if errors:
            return dict( name=workflow.name,
                             message="This workflow includes missing or invalid tools. It cannot be saved until the following steps are removed or the missing tools are enabled.",
                             errors=errors)
        # First pass to build step objects and populate basic values
        for key, step_dict in data['steps'].iteritems():
            # Create the model class for the step
            step = model.WorkflowStep()
            steps.append( step )
            steps_by_external_id[ step_dict['id' ] ] = step
            # FIXME: Position should be handled inside module
            step.position = step_dict['position']
            module = module_factory.from_dict( trans, step_dict )
            module.save_to_step( step )
            if step_dict.has_key('workflow_outputs'):
                for output_name in step_dict['workflow_outputs']:
                    m = model.WorkflowOutput(workflow_step = step, output_name = output_name)
                    trans.sa_session.add(m)
            if step.tool_errors:
                # DBTODO Check for conditional inputs here.
                workflow.has_errors = True
            # Stick this in the step temporarily
            step.temp_input_connections = step_dict['input_connections']
            # Save step annotation.
            annotation = step_dict[ 'annotation' ]
            if annotation:
                annotation = sanitize_html( annotation, 'utf-8', 'text/html' )
                self.add_item_annotation( trans.sa_session, trans.get_user(), step, annotation )
        # Second pass to deal with connections between steps
        for step in steps:
            # Input connections
            for input_name, conn_dict in step.temp_input_connections.iteritems():
                if conn_dict:
                    conn = model.WorkflowStepConnection()
                    conn.input_step = step
                    conn.input_name = input_name
                    conn.output_name = conn_dict['output_name']
                    conn.output_step = steps_by_external_id[ conn_dict['id'] ]
            del step.temp_input_connections
        # Order the steps if possible
        attach_ordered_steps( workflow, steps )
        # Connect up
        workflow.stored_workflow = stored
        stored.latest_workflow = workflow
        # Persist
        trans.sa_session.flush()
        # Return something informative
        errors = []
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
    def export( self, trans, id=None, **kwd ):
        """
        Handles download/export workflow command.
        """
        stored = self.get_stored_workflow( trans, id, check_ownership=False, check_accessible=True )
        return trans.fill_template( "/workflow/export.mako", item=stored, use_panels=True )
    @web.expose
    @web.require_login( "use workflows" )
    def import_from_myexp( self, trans, myexp_id, **kwd ):
        """
        Imports a workflow from the myExperiment website.
        Authenticates either by using HTTP basic, or with a cookie.
        !!! This isn't currently used. MyExperiment uses the generic import_workflow method !!!
        """
        # Parse parameters
        myexp_username = kwd.get( 'myexp_username', None )
        myexp_password = kwd.get( 'myexp_password', None )
        myexp_cookie = kwd.get( 'myexp_cookie', None )
        # Get workflow content.
        conn = httplib.HTTPConnection( trans.app.config.get( "myexperiment_url", self.__myexp_url ) )
        # NOTE: blocks web thread.
        headers = {}
        if myexp_username and myexp_password:
            auth_header = base64.b64encode( '%s:%s' % ( myexp_username, myexp_password ))
            headers = { "Authorization" : "Basic %s" % auth_header }
        elif myexp_cookie:
            headers = { "Cookie" : "myexperiment_session=%s" % myexp_cookie }
        conn.request( "GET", "/workflow.xml?id=%s&elements=content" % myexp_id, headers=headers )
        response = conn.getresponse()
        response_data = response.read()
        conn.close()
        if response.status == 200:
            parser = SingleTagContentsParser( "content" )
            parser.feed( response_data )
            workflow_content = base64.b64decode( parser.tag_content )
            # Process workflow JSON and create workflow.
            workflow_dict = from_json_string( workflow_content )
            # Create workflow.
            workflow, missing_tool_tups = self._workflow_from_dict( trans, workflow_dict, source="myExperiment" )
            workflow = workflow.latest_workflow
            if missing_tool_tups:
                # TODO: handle the case where the imported workflow requires tools that are not available in
                # the local Galaxy instance.
                pass
            
        # Provide user feedback.
        workflow_list_str = " <br>Return to <a href='%s'>workflow list." % url_for( action='list' )
        if response.status != 200:
            return trans.show_error_message( "There was a problem importing the workflow. Error: %s %s" % (response_data, workflow_list_str) )            
        if workflow.has_errors:
            return trans.show_warn_message( "Imported, but some steps in this workflow have validation errors. %s" % workflow_list_str )
        if workflow.has_cycles:
            return trans.show_warn_message( "Imported, but this workflow contains cycles. %s" % workflow_list_str )
        else:
            return trans.show_message( "Workflow '%s' imported. %s" % (workflow.name, workflow_list_str) )
    @web.expose
    @web.require_login( "use workflows" )
    def export_to_myexp( self, trans, id, myexp_username, myexp_password ):
        """
        Exports a workflow to myExperiment website.
        """

        # Load encoded workflow from database
        user = trans.get_user()
        id = trans.security.decode_id( id )
        trans.workflow_building_mode = True
        stored = trans.sa_session.query( model.StoredWorkflow ).get( id )
        self.security_check( trans, stored, False, True )

        # Convert workflow to dict.
        workflow_dict = self._workflow_to_dict( trans, stored )

        #
        # Create and submit workflow myExperiment request.
        #

        # Create workflow content JSON.
        workflow_content = simplejson.dumps( workflow_dict, indent=4, sort_keys=True )

        # Create myExperiment request.
        request_raw = trans.fill_template( "workflow/myexp_export.mako", \
                                            workflow_name=workflow_dict['name'], \
                                            workflow_description=workflow_dict['annotation'], \
                                            workflow_content=workflow_content
                                            )
        # strip() b/c myExperiment XML parser doesn't allow white space before XML; utf-8 handles unicode characters.
        request = unicode( request_raw.strip(), 'utf-8' )

        # Do request and get result.
        auth_header = base64.b64encode( '%s:%s' % ( myexp_username, myexp_password ))
        headers = { "Content-type": "text/xml", "Accept": "text/xml", "Authorization" : "Basic %s" % auth_header }
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
        workflow_list_str = " <br>Return to <a href='%s'>workflow list." % url_for( action='list' )
        if myexp_workflow_id:
            return trans.show_message( \
                """Workflow '%s' successfully exported to myExperiment. <br/>
                <a href="http://%s/workflows/%s">Click here to view the workflow on myExperiment</a> %s
                """ % ( stored.name, myexp_url, myexp_workflow_id, workflow_list_str ),
                use_panels=True )
        else:
            return trans.show_error_message( \
                "Workflow '%s' could not be exported to myExperiment. Error: %s %s" % \
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
        valid_chars = '.,^_-()[]0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        sname = stored.name
        sname = ''.join(c in valid_chars and c or '_' for c in sname)[0:150]
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
        webapp = kwd.get( 'webapp', 'galaxy' )
        message = kwd.get( 'message', '' )
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
            workflow_name = tool_shed_decode( workflow_name )
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
            workflow_url = '%s/workflow/import_workflow?repository_metadata_id=%s&workflow_name=%s&webapp=%s&open_for_url=true&no_reset=true' % \
                ( tool_shed_url, repository_metadata_id, tool_shed_encode( workflow_name ), webapp )
            response = urllib2.urlopen( workflow_url )
            workflow_text = response.read()
            response.close()
            import_button = True
        if import_button:
            workflow_data = None
            if url:
                # Load workflow from external URL
                # NOTE: blocks the web thread.
                try:
                    workflow_data = urllib2.urlopen( url ).read()
                except Exception, e:
                    message = "Failed to open URL: <b>%s</b><br>Exception: %s" % ( url, str( e ) )
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
                    uploaded_file_filename = file_data.filename
                    if os.path.getsize( os.path.abspath( uploaded_file_name ) ) > 0:
                        # We're reading the file as text so we can re-use the existing code below.
                        # This may not be ideal...
                        workflow_data = uploaded_file.read()
                    else:
                        message= 'You attempted to upload an empty file.'
                        status = 'error'
            if workflow_data:
                # Convert incoming workflow data from json
                try:
                    data = simplejson.loads( workflow_data )
                except Exception, e:
                    data = None
                    message = "The data content does not appear to be a Galaxy workflow.<br/>Exception: %s" % str( e )
                    status = 'error'
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
                        message += "Workflow <b>%s</b> imported successfully.  " % workflow.name
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
                            message += "You can likely install the required tools from one of the Galaxy tool sheds listed below.<br/><br/>"
                            for shed_name, shed_url in trans.app.tool_shed_registry.tool_sheds.items():
                                if shed_url.endswith( '/' ):
                                    shed_url = shed_url.rstrip( '/' )
                                    url = '%s/repository/find_tools?galaxy_url=%s&webapp=%s' % ( shed_url, url_for( '/', qualified=True ), webapp )
                                    if missing_tool_tups:
                                        url += '&tool_id='
                                    for missing_tool_tup in missing_tool_tups:
                                        missing_tool_id = missing_tool_tup[0]
                                        url += '%s,' % missing_tool_id
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
                                                                              webapp='galaxy',
                                                                              message=message,
                                                                              status=status ) )
                        else:
                            # TODO: Figure out what to do here...
                            pass
                    if tool_shed_url:
                        # We've received the textual representation of a workflow from a Galaxy tool shed.
                        message = "Workflow <b>%s</b> imported successfully." % workflow.name
                        url = '%s/workflow/view_workflow?repository_metadata_id=%s&workflow_name=%s&webapp=%s&message=%s' % \
                            ( tool_shed_url, repository_metadata_id, tool_shed_encode( workflow_name ), webapp, message )
                        return trans.response.send_redirect( url )
                    elif installed_repository_file:
                        # The workflow was read from a file included with an installed tool shed repository.
                        message = "Workflow <b>%s</b> imported successfully." % workflow.name
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
    @web.json
    def get_datatypes( self, trans ):
        ext_to_class_name = dict()
        classes = []
        for k, v in trans.app.datatypes_registry.datatypes_by_extension.iteritems():
            c = v.__class__
            ext_to_class_name[k] = c.__module__ + "." + c.__name__
            classes.append( c )
        class_to_classes = dict()
        def visit_bases( types, cls ):
            for base in cls.__bases__:
                if issubclass( base, Data ):
                    types.add( base.__module__ + "." + base.__name__ )
                visit_bases( types, base )
        for c in classes:
            n =  c.__module__ + "." + c.__name__
            types = set( [ n ] )
            visit_bases( types, c )
            class_to_classes[ n ] = dict( ( t, True ) for t in types )
        return dict( ext_to_class_name=ext_to_class_name, class_to_classes=class_to_classes )

    @web.expose
    def build_from_current_history( self, trans, job_ids=None, dataset_ids=None, workflow_name=None ):
        user = trans.get_user()
        history = trans.get_history()
        if not user:
            return trans.show_error_message( "Must be logged in to create workflows" )
        if ( job_ids is None and dataset_ids is None ) or workflow_name is None:
            jobs, warnings = get_job_dict( trans )
            # Render
            return trans.fill_template(
                        "workflow/build_from_current_history.mako",
                        jobs=jobs,
                        warnings=warnings,
                        history=history )
        else:
            # Ensure job_ids and dataset_ids are lists (possibly empty)
            if job_ids is None:
                job_ids = []
            elif type( job_ids ) is not list:
                job_ids = [ job_ids ]
            if dataset_ids is None:
                dataset_ids = []
            elif type( dataset_ids ) is not list:
                dataset_ids = [ dataset_ids ]
            # Convert both sets of ids to integers
            job_ids = [ int( id ) for id in job_ids ]
            dataset_ids = [ int( id ) for id in dataset_ids ]
            # Find each job, for security we (implicately) check that they are
            # associated witha job in the current history.
            jobs, warnings = get_job_dict( trans )
            jobs_by_id = dict( ( job.id, job ) for job in jobs.keys() )
            steps = []
            steps_by_job_id = {}
            hid_to_output_pair = {}
            # Input dataset steps
            for hid in dataset_ids:
                step = model.WorkflowStep()
                step.type = 'data_input'
                hid_to_output_pair[ hid ] = ( step, 'output' )
                steps.append( step )
            # Tool steps
            for job_id in job_ids:
                assert job_id in jobs_by_id, "Attempt to create workflow with job not connected to current history"
                job = jobs_by_id[ job_id ]
                tool = trans.app.toolbox.get_tool( job.tool_id )
                param_values = job.get_param_values( trans.app )
                associations = cleanup_param_values( tool.inputs, param_values )
                step = model.WorkflowStep()
                step.type = 'tool'
                step.tool_id = job.tool_id
                step.tool_inputs = tool.params_to_strings( param_values, trans.app )
                # NOTE: We shouldn't need to do two passes here since only
                #       an earlier job can be used as an input to a later
                #       job.
                for other_hid, input_name in associations:
                    if other_hid in hid_to_output_pair:
                        other_step, other_name = hid_to_output_pair[ other_hid ]
                        conn = model.WorkflowStepConnection()
                        conn.input_step = step
                        conn.input_name = input_name
                        # Should always be connected to an earlier step
                        conn.output_step = other_step
                        conn.output_name = other_name
                steps.append( step )
                steps_by_job_id[ job_id ] = step
                # Store created dataset hids
                for assoc in job.output_datasets:
                    hid_to_output_pair[ assoc.dataset.hid ] = ( step, assoc.name )
            # Workflow to populate
            workflow = model.Workflow()
            workflow.name = workflow_name
            # Order the steps if possible
            attach_ordered_steps( workflow, steps )
            # And let's try to set up some reasonable locations on the canvas
            # (these are pretty arbitrary values)
            levorder = order_workflow_steps_with_levels( steps )
            base_pos = 10
            for i, steps_at_level in enumerate( levorder ):
                for j, index in enumerate( steps_at_level ):
                    step = steps[ index ]
                    step.position = dict( top = ( base_pos + 120 * j ),
                                          left = ( base_pos + 220 * i ) )
            # Store it
            stored = model.StoredWorkflow()
            stored.user = user
            stored.name = workflow_name
            workflow.stored_workflow = stored
            stored.latest_workflow = workflow
            trans.sa_session.add( stored )
            trans.sa_session.flush()
            # Index page with message
            return trans.show_message( "Workflow '%s' created from current history." % workflow_name )
            ## return trans.show_ok_message( "<p>Workflow '%s' created.</p><p><a target='_top' href='%s'>Click to load in workflow editor</a></p>"
            ##     % ( workflow_name, web.url_for( action='editor', id=trans.security.encode_id(stored.id) ) ) )

    @web.expose
    def run( self, trans, id, history_id=None, hide_fixed_params=False, **kwargs ):
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
            error( "Workflow cannot be run because it does not have any steps" )
        #workflow = Workflow.from_simple( simplejson.loads( stored.encoded_value ), trans.app )
        if workflow.has_cycles:
            error( "Workflow cannot be run because it contains cycles" )
        if workflow.has_errors:
            error( "Workflow cannot be run because of validation errors in some steps" )
        # Build the state for each step
        errors = {}
        has_upgrade_messages = False
        has_errors = False
        saved_history = None
        if history_id is not None:
            saved_history = trans.get_history();
            try:
                decoded_history_id = trans.security.decode_id( history_id )
                history = trans.sa_session.query(trans.app.model.History).get(decoded_history_id)
                if history.user != trans.user and not trans.user_is_admin():
                    if trans.sa_session.query(trans.app.model.HistoryUserShareAssociation).filter_by(user=trans.user, history=history).count() == 0:
                        error("History is not owned by or shared with current user")
                trans.set_history(history)
            except TypeError:
                error("Malformed history id ( %s ) specified, unable to decode." % str( history_id ))
            except:
                error("That history does not exist.")
        try: # use a try/finally block to restore the user's current history
            if kwargs:
                # If kwargs were provided, the states for each step should have
                # been POSTed
                # Get the kwarg keys for data inputs
                input_keys = filter(lambda a: a.endswith('|input'), kwargs)
                # Example: prefixed='2|input'
                # Check if one of them is a list
                multiple_input_key = None
                multiple_inputs = [None]
                for input_key in input_keys:
                    if isinstance(kwargs[input_key], list):
                        multiple_input_key = input_key
                        multiple_inputs = kwargs[input_key]
                # List to gather values for the template
                invocations=[]
                for input_number, single_input in enumerate(multiple_inputs):
                    # Example: single_input='1', single_input='2', etc...
                    # 'Fix' the kwargs, to have only the input for this iteration
                    if multiple_input_key:
                        kwargs[multiple_input_key] = single_input
                    for step in workflow.steps:
                        step.upgrade_messages = {}
                        # Connections by input name
                        step.input_connections_by_name = \
                            dict( ( conn.input_name, conn ) for conn in step.input_connections )
                        # Extract just the arguments for this step by prefix
                        p = "%s|" % step.id
                        l = len(p)
                        step_args = dict( ( k[l:], v ) for ( k, v ) in kwargs.iteritems() if k.startswith( p ) )
                        step_errors = None
                        if step.type == 'tool' or step.type is None:
                            module = module_factory.from_workflow_step( trans, step )
                            # Fix any missing parameters
                            step.upgrade_messages = module.check_and_update_state()
                            if step.upgrade_messages:
                                has_upgrade_messages = True
                            # Any connected input needs to have value DummyDataset (these
                            # are not persisted so we need to do it every time)
                            module.add_dummy_datasets( connections=step.input_connections )
                            # Get the tool
                            tool = module.tool
                            # Get the state
                            step.state = state = module.state
                            # Get old errors
                            old_errors = state.inputs.pop( "__errors__", {} )
                            # Update the state
                            step_errors = tool.update_state( trans, tool.inputs, step.state.inputs, step_args,
                                                             update_only=True, old_errors=old_errors )
                        else:
                            # Fix this for multiple inputs
                            module = step.module = module_factory.from_workflow_step( trans, step )
                            state = step.state = module.decode_runtime_state( trans, step_args.pop( "tool_state" ) )
                            step_errors = module.update_runtime_state( trans, state, step_args )
                        if step_errors:
                            errors[step.id] = state.inputs["__errors__"] = step_errors
                    if 'run_workflow' in kwargs and not errors:
                        new_history = None
                        if 'new_history' in kwargs:
                            if 'new_history_name' in kwargs and kwargs['new_history_name'] != '':
                                nh_name = kwargs['new_history_name']
                            else:
                                nh_name = "History from %s workflow" % workflow.name
                            if multiple_input_key:
                                mx_ds_name = trans.sa_session.query(trans.app.model.HistoryDatasetAssociation).get( single_input ).name
                                nh_name = '%s on %s' % (nh_name, mx_ds_name)
                            new_history = trans.app.model.History( user=trans.user, name=nh_name )
                            trans.sa_session.add( new_history )
                        # Run each step, connecting outputs to inputs
                        workflow_invocation = model.WorkflowInvocation()
                        workflow_invocation.workflow = workflow
                        outputs = odict()
                        for i, step in enumerate( workflow.steps ):
                            # Execute module
                            job = None
                            if step.type == 'tool' or step.type is None:
                                tool = trans.app.toolbox.get_tool( step.tool_id )
                                # Connect up
                                def callback( input, value, prefixed_name, prefixed_label ):
                                    if isinstance( input, DataToolParameter ):
                                        if prefixed_name in step.input_connections_by_name:
                                            conn = step.input_connections_by_name[ prefixed_name ]
                                            return outputs[ conn.output_step.id ][ conn.output_name ]
                                try:
                                    visit_input_values( tool.inputs, step.state.inputs, callback )
                                except KeyError, k:
                                    error( "Error due to input mapping of '%s' in '%s'.  A common cause of this is conditional outputs that cannot be determined until runtime, please review your workflow." % (tool.name, k.message))
                                # Execute it
                                job, out_data = tool.execute( trans, step.state.inputs, history=new_history)
                                outputs[ step.id ] = out_data
                                # Create new PJA associations with the created job, to be run on completion.
                                # PJA Parameter Replacement (only applies to immediate actions-- rename specifically, for now)
                                # Pass along replacement dict with the execution of the PJA so we don't have to modify the object.
                                replacement_dict = {}
                                for k, v in kwargs.iteritems():
                                    if k.startswith('wf_parm|'):
                                        replacement_dict[k[8:]] = v
                                for pja in step.post_job_actions:
                                    if pja.action_type in ActionBox.immediate_actions:
                                        ActionBox.execute(trans.app, trans.sa_session, pja, job, replacement_dict)
                                    else:
                                        job.add_post_job_action(pja)
                            else:
                                job, out_data = step.module.execute( trans, step.state )
                                outputs[ step.id ] = out_data
                                if new_history:
                                    for input_dataset_hda in out_data.values():
                                        new_hda = input_dataset_hda.copy( copy_children=True )
                                        new_history.add_dataset(new_hda)
                                        outputs[ step.id ]['input_ds_copy'] = new_hda
                            # Record invocation
                            workflow_invocation_step = model.WorkflowInvocationStep()
                            workflow_invocation_step.workflow_invocation = workflow_invocation
                            workflow_invocation_step.workflow_step = step
                            workflow_invocation_step.job = job
                        # All jobs ran sucessfully, so we can save now
                        trans.sa_session.add( workflow_invocation )
                        invocations.append({'outputs': outputs,
                                            'new_history': new_history})
                        trans.sa_session.flush()
                if invocations:
                    return trans.fill_template( "workflow/run_complete.mako",
                                                    workflow=stored,
                                                    invocations=invocations )
            else:
                # Prepare each step
                missing_tools = []
                for step in workflow.steps:
                    step.upgrade_messages = {}
                    # Contruct modules
                    if step.type == 'tool' or step.type is None:
                        # Restore the tool state for the step
                        step.module = module_factory.from_workflow_step( trans, step )
                        if not step.module:
                            if step.tool_id not in missing_tools:
                                missing_tools.append(step.tool_id)
                            continue
                        step.upgrade_messages = step.module.check_and_update_state()
                        if step.upgrade_messages:
                            has_upgrade_messages = True
                        # Any connected input needs to have value DummyDataset (these
                        # are not persisted so we need to do it every time)
                        step.module.add_dummy_datasets( connections=step.input_connections )
                        # Store state with the step
                        step.state = step.module.state
                        # Error dict
                        if step.tool_errors:
                            has_errors = True
                            errors[step.id] = step.tool_errors
                    else:
                        ## Non-tool specific stuff?
                        step.module = module_factory.from_workflow_step( trans, step )
                        step.state = step.module.get_runtime_state()
                    # Connections by input name
                    step.input_connections_by_name = dict( ( conn.input_name, conn ) for conn in step.input_connections )
                if missing_tools:
                    stored.annotation = self.get_item_annotation_str( trans.sa_session, trans.user, stored )
                    return trans.fill_template("workflow/run.mako", steps=[], workflow=stored, missing_tools = missing_tools)
            # Render the form
            stored.annotation = self.get_item_annotation_str( trans.sa_session, trans.user, stored )
            return trans.fill_template(
                        "workflow/run.mako",
                        steps=workflow.steps,
                        workflow=stored,
                        has_upgrade_messages=has_upgrade_messages,
                        errors=errors,
                        incoming=kwargs,
                        history_id=history_id,
                        hide_fixed_params=hide_fixed_params,
                        enable_unique_defaults=trans.app.config.enable_unique_workflow_defaults)
        finally:
            # restore the active history
            if saved_history is not None:
                trans.set_history(saved_history)

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
        has_errors = False
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
                        m = model.WorkflowOutput(workflow_step_id = int(step.id), output_name = outputname)
                        trans.sa_session.add(m)
        # Prepare each step
        trans.sa_session.flush()
        for step in workflow.steps:
            step.upgrade_messages = {}
            # Contruct modules
            if step.type == 'tool' or step.type is None:
                # Restore the tool state for the step
                step.module = module_factory.from_workflow_step( trans, step )
                # Fix any missing parameters
                step.upgrade_messages = step.module.check_and_update_state()
                if step.upgrade_messages:
                    has_upgrade_messages = True
                # Any connected input needs to have value DummyDataset (these
                # are not persisted so we need to do it every time)
                step.module.add_dummy_datasets( connections=step.input_connections )
                # Store state with the step
                step.state = step.module.state
                # Error dict
                if step.tool_errors:
                    has_errors = True
                    errors[step.id] = step.tool_errors
            else:
                ## Non-tool specific stuff?
                step.module = module_factory.from_workflow_step( trans, step )
                step.state = step.module.get_runtime_state()
            # Connections by input name
            step.input_connections_by_name = dict( ( conn.input_name, conn ) for conn in step.input_connections )
        # Render the form
        return trans.fill_template(
                    "workflow/tag_outputs.mako",
                    steps=workflow.steps,
                    workflow=stored,
                    has_upgrade_messages=has_upgrade_messages,
                    errors=errors,
                    incoming=kwargs )

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
            return trans.show_message( "Menu updated", refresh_frames=['tools'] )
        else:
            user = trans.get_user()
            ids_in_menu = set( [ x.stored_workflow_id for x in user.stored_workflow_menu_entries ] )
            workflows = trans.sa_session.query( model.StoredWorkflow ) \
                .filter_by( user=user, deleted=False ) \
                .order_by( desc( model.StoredWorkflow.table.c.update_time ) ) \
                .all()
            shared_by_others = trans.sa_session \
                .query( model.StoredWorkflowUserShareAssociation ) \
                .filter_by( user=user ) \
                .filter( model.StoredWorkflow.deleted == False ) \
                .all()
            return trans.fill_template( "workflow/configure_menu.mako",
                                        workflows=workflows,
                                        shared_by_others=shared_by_others,
                                        ids_in_menu=ids_in_menu )

    def _workflow_to_dict( self, trans, stored ):
        """
        Converts a workflow to a dict of attributes suitable for exporting.
        """
        workflow = stored.latest_workflow
        workflow_annotation = self.get_item_annotation_obj( trans.sa_session, trans.user, stored )
        annotation_str = ""
        if workflow_annotation:
            annotation_str = workflow_annotation.annotation
        # Pack workflow data into a dictionary and return
        data = {}
        data['a_galaxy_workflow'] = 'true' # Placeholder for identifying galaxy workflow
        data['format-version'] = "0.1"
        data['name'] = workflow.name
        data['annotation'] = annotation_str
        data['steps'] = {}
        # For each step, rebuild the form and encode the state
        for step in workflow.steps:
            # Load from database representation
            module = module_factory.from_workflow_step( trans, step )
            # Get user annotation.
            step_annotation = self.get_item_annotation_obj(trans.sa_session, trans.user, step )
            annotation_str = ""
            if step_annotation:
                annotation_str = step_annotation.annotation
            # Step info
            step_dict = {
                'id': step.order_index,
                'type': module.type,
                'tool_id': module.get_tool_id(),
                'tool_version' : step.tool_version,
                'name': module.get_name(),
                'tool_state': module.get_state( secure=False ),
                'tool_errors': module.get_errors(),
                ## 'data_inputs': module.get_data_inputs(),
                ## 'data_outputs': module.get_data_outputs(),
                'annotation' : annotation_str
            }
            # Add post-job actions to step dict.
            if module.type == 'tool':
                pja_dict = {}
                for pja in step.post_job_actions:
                    pja_dict[pja.action_type+pja.output_name] = dict( action_type = pja.action_type,
                                                                      output_name = pja.output_name,
                                                                      action_arguments = pja.action_arguments )
                step_dict[ 'post_job_actions' ] = pja_dict
            # Data inputs
            step_dict['inputs'] = []
            if module.type == "data_input":
                # Get input dataset name; default to 'Input Dataset'
                name = module.state.get( 'name', 'Input Dataset')
                step_dict['inputs'].append( { "name" : name, "description" : annotation_str } )
            else:
                # Step is a tool and may have runtime inputs.
                for name, val in module.state.inputs.items():
                    input_type = type( val )
                    if input_type == RuntimeValue:
                        step_dict['inputs'].append( { "name" : name, "description" : "runtime parameter for tool %s" % module.get_name() } )
                    elif input_type == dict:
                        # Input type is described by a dict, e.g. indexed parameters.
                        for partname, partval in val.items():
                            if type( partval ) == RuntimeValue:
                                step_dict['inputs'].append( { "name" : name, "description" : "runtime parameter for tool %s" % module.get_name() } )
            # User outputs
            step_dict['user_outputs'] = []
            """
            module_outputs = module.get_data_outputs()
            step_outputs = trans.sa_session.query( WorkflowOutput ).filter( step=step )
            for output in step_outputs:
                name = output.output_name
                annotation = ""
                for module_output in module_outputs:
                    if module_output.get( 'name', None ) == name:
                        output_type = module_output.get( 'extension', '' )
                        break
                data['outputs'][name] = { 'name' : name, 'annotation' : annotation, 'type' : output_type }
            """

            # All step outputs
            step_dict['outputs'] = []
            if type( module ) is ToolModule:
                for output in module.get_data_outputs():
                    step_dict['outputs'].append( { 'name' : output['name'], 'type' : output['extensions'][0] } )
            # Connections
            input_connections = step.input_connections
            if step.type is None or step.type == 'tool':
                # Determine full (prefixed) names of valid input datasets
                data_input_names = {}
                def callback( input, value, prefixed_name, prefixed_label ):
                    if isinstance( input, DataToolParameter ):
                        data_input_names[ prefixed_name ] = True
                visit_input_values( module.tool.inputs, module.state.inputs, callback )
                # Filter
                # FIXME: this removes connection without displaying a message currently!
                input_connections = [ conn for conn in input_connections if conn.input_name in data_input_names ]
            # Encode input connections as dictionary
            input_conn_dict = {}
            for conn in input_connections:
                input_conn_dict[ conn.input_name ] = \
                    dict( id=conn.output_step.order_index, output_name=conn.output_name )
            step_dict['input_connections'] = input_conn_dict
            # Position
            step_dict['position'] = step.position
            # Add to return value
            data['steps'][step.order_index] = step_dict
        return data
    def _workflow_from_dict( self, trans, data, source=None, add_to_menu=False ):
        """
        Creates a workflow from a dict. Created workflow is stored in the database and returned.
        """
        # Put parameters in workflow mode
        trans.workflow_building_mode = True
        # Create new workflow from incoming dict
        workflow = model.Workflow()
        # If there's a source, put it in the workflow name.
        if source:
            name = "%s (imported from %s)" % ( data['name'], source )
        else:
            name = data['name']
        workflow.name = name
        # Assume no errors until we find a step that has some
        workflow.has_errors = False
        # Create each step
        steps = []
        # The editor will provide ids for each step that we don't need to save,
        # but do need to use to make connections
        steps_by_external_id = {}
        # Keep track of tools required by the workflow that are not available in
        # the local Galaxy instance.  Each tuple in the list of missing_tool_tups
        # will be ( tool_id, tool_name, tool_version ).
        missing_tool_tups = []
        # First pass to build step objects and populate basic values
        for key, step_dict in data[ 'steps' ].iteritems():
            # Create the model class for the step
            step = model.WorkflowStep()
            steps.append( step )
            steps_by_external_id[ step_dict['id' ] ] = step
            # FIXME: Position should be handled inside module
            step.position = step_dict['position']
            module = module_factory.from_dict( trans, step_dict, secure=False )
            if module.type == 'tool' and module.tool is None:
                # A required tool is not available in the local Galaxy instance.
                missing_tool_tup = ( step_dict[ 'tool_id' ], step_dict[ 'name' ], step_dict[ 'tool_version' ] )
                if missing_tool_tup not in missing_tool_tups:
                    missing_tool_tups.append( missing_tool_tup )
            module.save_to_step( step )
            if step.tool_errors:
                workflow.has_errors = True
            # Stick this in the step temporarily
            step.temp_input_connections = step_dict['input_connections']
            # Save step annotation.
            annotation = step_dict[ 'annotation' ]
            if annotation:
                annotation = sanitize_html( annotation, 'utf-8', 'text/html' )
                self.add_item_annotation( trans.sa_session, trans.get_user(), step, annotation )
            # Unpack and add post-job actions.
            post_job_actions = step_dict.get( 'post_job_actions', {} )
            for name, pja_dict in post_job_actions.items():
                pja = PostJobAction( pja_dict[ 'action_type' ],
                                     step, pja_dict[ 'output_name' ],
                                     pja_dict[ 'action_arguments' ] )
        # Second pass to deal with connections between steps
        for step in steps:
            # Input connections
            for input_name, conn_dict in step.temp_input_connections.iteritems():
                if conn_dict:
                    conn = model.WorkflowStepConnection()
                    conn.input_step = step
                    conn.input_name = input_name
                    conn.output_name = conn_dict['output_name']
                    conn.output_step = steps_by_external_id[ conn_dict['id'] ]
            del step.temp_input_connections
        # Order the steps if possible
        attach_ordered_steps( workflow, steps )
        # Connect up
        stored = model.StoredWorkflow()
        stored.name = workflow.name
        workflow.stored_workflow = stored
        stored.latest_workflow = workflow
        stored.user = trans.user
        # Persist
        trans.sa_session.add( stored )
        trans.sa_session.flush()

        if add_to_menu:
            if trans.user.stored_workflow_menu_entries == None:
                trans.user.stored_workflow_menu_entries = []
            menuEntry = model.StoredWorkflowMenuEntry()
            menuEntry.stored_workflow = stored
            trans.user.stored_workflow_menu_entries.append( menuEntry )
            trans.sa_session.flush()

        return stored, missing_tool_tups

## ---- Utility methods -------------------------------------------------------

def attach_ordered_steps( workflow, steps ):
    ordered_steps = order_workflow_steps( steps )
    if ordered_steps:
        workflow.has_cycles = False
        for i, step in enumerate( ordered_steps ):
            step.order_index = i
            workflow.steps.append( step )
    else:
        workflow.has_cycles = True
        workflow.steps = steps

def edgelist_for_workflow_steps( steps ):
    """
    Create a list of tuples representing edges between `WorkflowSteps` based
    on associated `WorkflowStepConnection`s
    """
    edges = []
    steps_to_index = dict( ( step, i ) for i, step in enumerate( steps ) )
    for step in steps:
        edges.append( ( steps_to_index[step], steps_to_index[step] ) )
        for conn in step.input_connections:
            edges.append( ( steps_to_index[conn.output_step], steps_to_index[conn.input_step] ) )
    return edges

def order_workflow_steps( steps ):
    """
    Perform topological sort of the steps, return ordered or None
    """
    position_data_available = True
    for step in steps:
        if not step.position or not 'left' in step.position or not 'top' in step.position:
            position_data_available = False
    if position_data_available:
        steps.sort(cmp=lambda s1,s2: cmp( math.sqrt(s1.position['left']**2 + s1.position['top']**2), math.sqrt(s2.position['left']**2 + s2.position['top']**2)))
    try:
        edges = edgelist_for_workflow_steps( steps )
        node_order = topsort( edges )
        return [ steps[i] for i in node_order ]
    except CycleError:
        return None

def order_workflow_steps_with_levels( steps ):
    try:
        return topsort_levels( edgelist_for_workflow_steps( steps ) )
    except CycleError:
        return None

class FakeJob( object ):
    """
    Fake job object for datasets that have no creating_job_associations,
    they will be treated as "input" datasets.
    """
    def __init__( self, dataset ):
        self.is_fake = True
        self.id = "fake_%s" % dataset.id

def get_job_dict( trans ):
    """
    Return a dictionary of Job -> [ Dataset ] mappings, for all finished
    active Datasets in the current history and the jobs that created them.
    """
    history = trans.get_history()
    # Get the jobs that created the datasets
    warnings = set()
    jobs = odict()
    for dataset in history.active_datasets:
        # FIXME: Create "Dataset.is_finished"
        if dataset.state in ( 'new', 'running', 'queued' ):
            warnings.add( "Some datasets still queued or running were ignored" )
            continue

        #if this hda was copied from another, we need to find the job that created the origial hda
        job_hda = dataset
        while job_hda.copied_from_history_dataset_association:
            job_hda = job_hda.copied_from_history_dataset_association

        if not job_hda.creating_job_associations:
            jobs[ FakeJob( dataset ) ] = [ ( None, dataset ) ]

        for assoc in job_hda.creating_job_associations:
            job = assoc.job
            if job in jobs:
                jobs[ job ].append( ( assoc.name, dataset ) )
            else:
                jobs[ job ] = [ ( assoc.name, dataset ) ]
    return jobs, warnings

def cleanup_param_values( inputs, values ):
    """
    Remove 'Data' values from `param_values`, along with metadata cruft,
    but track the associations.
    """
    associations = []
    names_to_clean = []
    # dbkey is pushed in by the framework
    if 'dbkey' in values:
        del values['dbkey']
    root_values = values
    # Recursively clean data inputs and dynamic selects
    def cleanup( prefix, inputs, values ):
        for key, input in inputs.items():
            if isinstance( input, ( SelectToolParameter, DrillDownSelectToolParameter ) ):
                if input.is_dynamic and not isinstance( values[key], UnvalidatedValue ):
                    values[key] = UnvalidatedValue( values[key] )
            if isinstance( input, DataToolParameter ):
                tmp = values[key]
                values[key] = None
                # HACK: Nested associations are not yet working, but we
                #       still need to clean them up so we can serialize
                # if not( prefix ):
                if tmp: #this is false for a non-set optional dataset
                    associations.append( ( tmp.hid, prefix + key ) )
                # Cleanup the other deprecated crap associated with datasets
                # as well. Worse, for nested datasets all the metadata is
                # being pushed into the root. FIXME: MUST REMOVE SOON
                key = prefix + key + "_"
                for k in root_values.keys():
                    if k.startswith( key ):
                        del root_values[k]
            elif isinstance( input, Repeat ):
                group_values = values[key]
                for i, rep_values in enumerate( group_values ):
                    rep_index = rep_values['__index__']
                    cleanup( "%s%s_%d|" % (prefix, key, rep_index ), input.inputs, group_values[i] )
            elif isinstance( input, Conditional ):
                group_values = values[input.name]
                current_case = group_values['__current_case__']
                cleanup( "%s%s|" % ( prefix, key ), input.cases[current_case].inputs, group_values )
    cleanup( "", inputs, values )
    return associations

