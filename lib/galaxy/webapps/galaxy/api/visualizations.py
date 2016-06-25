"""
Visualizations resource control over the API.

NOTE!: this is a work in progress and functionality and data structures
may change often.
"""
from six import string_types

from galaxy.web.base.controller import BaseAPIController
from galaxy.web.base.controller import UsesVisualizationMixin
from galaxy.web.base.controller import SharableMixin
from galaxy.model.item_attrs import UsesAnnotations

from galaxy.web import _future_expose_api as expose_api
from galaxy import web
from galaxy import util
from galaxy import exceptions
import json
import logging
log = logging.getLogger( __name__ )


class VisualizationsController( BaseAPIController, UsesVisualizationMixin, SharableMixin, UsesAnnotations ):
    """
    RESTful controller for interactions with visualizations.
    """

    @expose_api
    def index( self, trans, **kwargs ):
        """
        GET /api/visualizations:
        """
        rval = []
        user = trans.user

        # TODO: search for: title, made by user, creation time range, type (vis name), dbkey, etc.
        # TODO: limit, offset, order_by
        # TODO: deleted

        # this is the default search - user's vis, vis shared with user, published vis
        visualizations = self.get_visualizations_by_user( trans, user )
        visualizations += self.get_visualizations_shared_with_user( trans, user )
        visualizations += self.get_published_visualizations( trans, exclude_user=user )
        # TODO: the admin case - everything

        for visualization in visualizations:
            item = self.get_visualization_summary_dict( visualization )
            item = trans.security.encode_dict_ids( item )
            item[ 'url' ] = web.url_for( 'visualization', id=item[ 'id' ] )
            rval.append( item )

        return rval

    @expose_api
    def show( self, trans, id, **kwargs ):
        """
        GET /api/visualizations/{viz_id}
        """
        # TODO: revisions should be a contents/nested controller like viz/xxx/r/xxx)?
        # the important thing is the config
        rval = {}
        # TODO:?? /api/visualizations/registry -> json of registry.listings?

        visualization = self.get_visualization( trans, id, check_ownership=False, check_accessible=True )
        dictionary = trans.security.encode_dict_ids( self.get_visualization_dict( visualization ) )
        dictionary[ 'url' ] = web.url_for( controller='visualization',
                                           action="display_by_username_and_slug", username=visualization.user.username, slug=visualization.slug )
        dictionary[ 'annotation' ] = self.get_item_annotation_str( trans.sa_session, trans.user, visualization )

        # need to encode ids in revisions as well
        encoded_revisions = []
        for revision in dictionary[ 'revisions' ]:
            # NOTE: does not encode ids inside the configs
            encoded_revisions.append( trans.security.encode_id( revision ) )
        dictionary[ 'revisions' ] = encoded_revisions
        dictionary[ 'latest_revision' ] = trans.security.encode_dict_ids( dictionary[ 'latest_revision' ] )

        rval = dictionary
        return rval

    @expose_api
    def create( self, trans, payload, **kwargs ):
        """
        POST /api/visualizations
        creates a new visualization using the given payload

        POST /api/visualizations?import_id={encoded_visualization_id}
        imports a copy of an existing visualization into the user's workspace
        """
        rval = None

        if 'import_id' in payload:
            import_id = payload( 'import_id' )
            visualization = self.import_visualization( trans, import_id, user=trans.user )

        else:
            payload = self._validate_and_parse_payload( payload )
            # must have a type (I've taken this to be the visualization name)
            if 'type' not in payload:
                raise exceptions.RequestParameterMissingException( "key/value 'type' is required" )
            vis_type = payload.pop( 'type', False )

            payload[ 'save' ] = True
            try:
                # generate defaults - this will err if given a weird key?
                visualization = self.create_visualization( trans, vis_type, **payload )
            except ValueError as val_err:
                raise exceptions.RequestParameterMissingException( str( val_err ) )

        rval = { 'id' : trans.security.encode_id( visualization.id ) }

        return rval

    @expose_api
    def update( self, trans, id, payload, **kwargs ):
        """
        PUT /api/visualizations/{encoded_visualization_id}
        """
        rval = None

        payload = self._validate_and_parse_payload( payload )

        # there's a differentiation here between updating the visualiztion and creating a new revision
        #   that needs to be handled clearly here
        # or alternately, using a different controller like PUT /api/visualizations/{id}/r/{id}

        # TODO: consider allowing direct alteration of revisions title (without a new revision)
        #   only create a new revsion on a different config

        # only update owned visualizations
        visualization = self.get_visualization( trans, id, check_ownership=True )
        title = payload.get( 'title', visualization.latest_revision.title )
        dbkey = payload.get( 'dbkey', visualization.latest_revision.dbkey )
        config = payload.get( 'config', visualization.latest_revision.config )

        latest_config = visualization.latest_revision.config
        if( ( title != visualization.latest_revision.title ) or
                ( dbkey != visualization.latest_revision.dbkey ) or
                ( json.dumps( config ) != json.dumps( latest_config ) ) ):
            revision = self.add_visualization_revision( trans, visualization, config, title, dbkey )
            rval = { 'id' : id, 'revision' : revision.id }

        # allow updating vis title
        visualization.title = title
        trans.sa_session.flush()

        return rval

    def _validate_and_parse_payload( self, payload ):
        """
        Validate and parse incomming data payload for a visualization.
        """
        # This layer handles (most of the stricter idiot proofing):
        #   - unknown/unallowed keys
        #   - changing data keys from api key to attribute name
        #   - protection against bad data form/type
        #   - protection against malicious data content
        # all other conversions and processing (such as permissions, etc.) should happen down the line

        # keys listed here don't error when attempting to set, but fail silently
        #   this allows PUT'ing an entire model back to the server without attribute errors on uneditable attrs
        valid_but_uneditable_keys = (
            'id', 'model_class'
            # TODO: fill out when we create to_dict, get_dict, whatevs
        )
        # TODO: deleted
        # TODO: importable
        ValidationError = exceptions.RequestParameterInvalidException

        validated_payload = {}
        for key, val in payload.items():
            # TODO: validate types in VALID_TYPES/registry names at the mixin/model level?
            if key == 'type':
                if not isinstance( val, string_types ):
                    raise ValidationError( '%s must be a string or unicode: %s' % ( key, str( type( val ) ) ) )
                val = util.sanitize_html.sanitize_html( val, 'utf-8' )
            elif key == 'config':
                if not isinstance( val, dict ):
                    raise ValidationError( '%s must be a dictionary: %s' % ( key, str( type( val ) ) ) )

            elif key == 'annotation':
                if not isinstance( val, string_types ):
                    raise ValidationError( '%s must be a string or unicode: %s' % ( key, str( type( val ) ) ) )
                val = util.sanitize_html.sanitize_html( val, 'utf-8' )

            # these are keys that actually only be *updated* at the revision level and not here
            #   (they are still valid for create, tho)
            elif key == 'title':
                if not isinstance( val, string_types ):
                    raise ValidationError( '%s must be a string or unicode: %s' % ( key, str( type( val ) ) ) )
                val = util.sanitize_html.sanitize_html( val, 'utf-8' )
            elif key == 'slug':
                if not isinstance( val, string_types ):
                    raise ValidationError( '%s must be a string: %s' % ( key, str( type( val ) ) ) )
                val = util.sanitize_html.sanitize_html( val, 'utf-8' )
            elif key == 'dbkey':
                if not isinstance( val, string_types ):
                    raise ValidationError( '%s must be a string or unicode: %s' % ( key, str( type( val ) ) ) )
                val = util.sanitize_html.sanitize_html( val, 'utf-8' )

            elif key not in valid_but_uneditable_keys:
                continue
                # raise AttributeError( 'unknown key: %s' %( str( key ) ) )

            validated_payload[ key ] = val
        return validated_payload
