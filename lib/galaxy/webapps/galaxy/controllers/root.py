"""
Contains the main interface in the Universe class
"""
import cgi
import os
import urllib

from paste.httpexceptions import HTTPNotFound, HTTPBadGateway

from galaxy.web.base.controller import BaseUIController, UsesHistoryDatasetAssociationMixin, UsesHistoryMixin
from galaxy import managers

from galaxy import web
from galaxy.web import url_for
from galaxy.model.item_attrs import UsesAnnotations
from galaxy import util
from galaxy.util import listify, Params, string_as_bool, string_as_bool_or_none
from galaxy.util.json import dumps

import logging
log = logging.getLogger( __name__ )

class RootController( BaseUIController, UsesHistoryMixin, UsesHistoryDatasetAssociationMixin, UsesAnnotations ):
    """
    Controller class that maps to the url root of Galaxy (i.e. '/').
    """
    def __init__( self, app ):
        super( RootController, self ).__init__( app )
        self.mgrs = util.bunch.Bunch(
            histories=managers.histories.HistoryManager()
        )

    @web.expose
    def default(self, trans, target1=None, target2=None, **kwd):
        """Called on any url that does not match a controller method.
        """
        raise HTTPNotFound( 'This link may not be followed from within Galaxy.' )

    @web.expose
    def index(self, trans, id=None, tool_id=None, mode=None, workflow_id=None, m_c=None, m_a=None, **kwd):
        """
        Called on the root url to display the main Galaxy page.
        """
        return trans.fill_template( "root/index.mako",
                                    tool_id=tool_id,
                                    workflow_id=workflow_id,
                                    m_c=m_c, m_a=m_a,
                                    params=kwd )

    ## ---- Tool related -----------------------------------------------------

    @web.json
    def tool_search( self, trans, **kwd ):
        """Searches the tool database and returns data for any tool
        whose text matches the query.

        Data are returned in JSON format.
        """
        query = kwd.get( 'query', '' )
        tags = listify( kwd.get( 'tags[]', [] ) )
        trans.log_action( trans.get_user(), "tool_search.search", "", { "query" : query, "tags" : tags } )
        results = []
        if tags:
            tags = trans.sa_session.query( trans.app.model.Tag ).filter( trans.app.model.Tag.name.in_( tags ) ).all()
            for tagged_tool_il in [ tag.tagged_tools for tag in tags ]:
                for tagged_tool in tagged_tool_il:
                    if tagged_tool.tool_id not in results:
                        results.append( tagged_tool.tool_id )
            if trans.user:
                trans.user.preferences['selected_tool_tags'] = ','.join( [ tag.name for tag in tags ] )
                trans.sa_session.flush()
        elif trans.user:
            trans.user.preferences['selected_tool_tags'] = ''
            trans.sa_session.flush()
        if len( query ) > 2:
            search_results = trans.app.toolbox_search.search( query )
            if 'tags[]' in kwd:
                results = filter( lambda x: x in results, search_results )
            else:
                results = search_results
        return results

    @web.expose
    def tool_help( self, trans, id ):
        """Return help page for tool identified by 'id' if available
        """
        toolbox = self.get_toolbox()
        tool = toolbox.get_tool( id )
        yield "<html><body>"
        if not tool:
            #TODO: arent tool ids strings now?
            yield "Unknown tool id '%d'" % id
        elif tool.help:
            yield tool.help
        else:
            yield "No additional help available for tool '%s'" % tool.name
        yield "</body></html>"

    ## ---- Root history display ---------------------------------------------
    def history_as_xml( self, trans, show_deleted=None, show_hidden=None ):
        if trans.app.config.require_login and not trans.user:
            return trans.fill_template( '/no_access.mako', message = 'Please log in to access Galaxy histories.' )

        history = trans.get_history( create=True )
        trans.response.set_content_type('text/xml')
        return trans.fill_template_mako( "root/history_as_xml.mako",
                                          history=history,
                                          show_deleted=string_as_bool( show_deleted ),
                                          show_hidden=string_as_bool( show_hidden ) )

    @web.expose
    def history( self, trans, as_xml=False, show_deleted=None, show_hidden=None, **kwd ):
        """
        Display the current history in its own page or as xml.
        """
        if as_xml:
            return self.history_as_xml( trans,
                show_deleted=string_as_bool( show_deleted ), show_hidden=string_as_bool( show_hidden ) )

        if trans.app.config.require_login and not trans.user:
            return trans.fill_template( '/no_access.mako', message = 'Please log in to access Galaxy histories.' )

        # get all datasets server-side, client-side will get flags and render appropriately
        show_deleted = string_as_bool_or_none( show_deleted )
        show_purged  = show_deleted
        show_hidden  = string_as_bool_or_none( show_hidden )

        history_dictionary = {}
        hda_dictionaries = []
        try:
            history_data = self.mgrs.histories._get_history_data( trans, trans.get_history( create=True ) )
            history_dictionary = history_data[ 'history' ]
            hda_dictionaries   = history_data[ 'contents' ]

        except Exception, exc:
            user_id = str( trans.user.id ) if trans.user else '(anonymous)'
            log.exception( 'Error bootstrapping history for user %s: %s', user_id, str( exc ) )
            history_dictionary[ 'error' ] = ( 'An error occurred getting the history data from the server. '
                                            + 'Please contact a Galaxy administrator if the problem persists.' )

        return trans.fill_template_mako( "root/history.mako",
            history = history_dictionary, hdas = hda_dictionaries,
            show_deleted=show_deleted, show_hidden=show_hidden )


    ## ---- Dataset display / editing ----------------------------------------
    @web.expose
    def display( self, trans, id=None, hid=None, tofile=None, toext=".txt", encoded_id=None, **kwd ):
        """Returns data directly into the browser.

        Sets the mime-type according to the extension.

        Used by the twill tool test driver - used anywhere else? Would like to drop hid
        argument and path if unneeded now. Likewise, would like to drop encoded_id=XXX
        and use assume id is encoded (likely id wouldn't be coming in encoded if this
        is used anywhere else though.)
        """
        #TODO: unencoded id
        if hid is not None:
            try:
                hid = int( hid )
            except:
                return "hid '%s' is invalid" % str( hid )
            history = trans.get_history()
            for dataset in history.datasets:
                if dataset.hid == hid:
                    data = dataset
                    break
            else:
                raise Exception( "No dataset with hid '%d'" % hid )
        else:
            if encoded_id and not id:
                id = trans.security.decode_id( encoded_id )
            try:
                data = trans.sa_session.query( self.app.model.HistoryDatasetAssociation ).get( id )
            except:
                return "Dataset id '%s' is invalid" % str( id )
        if data:
            current_user_roles = trans.get_current_user_roles()
            if trans.app.security_agent.can_access_dataset( current_user_roles, data.dataset ):
                trans.response.set_content_type(data.get_mime())
                if tofile:
                    fStat = os.stat(data.file_name)
                    trans.response.headers['Content-Length'] = int(fStat.st_size)
                    if toext[0:1] != ".":
                        toext = "." + toext
                    valid_chars = '.,^_-()[]0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
                    fname = data.name
                    fname = ''.join(c in valid_chars and c or '_' for c in fname)[0:150]
                    trans.response.headers["Content-Disposition"] = 'attachment; filename="GalaxyHistoryItem-%s-[%s]%s"' % (data.hid, fname, toext)
                trans.log_event( "Display dataset id: %s" % str(id) )
                try:
                    return open( data.file_name )
                except:
                    return "This dataset contains no content"
            else:
                return "You are not allowed to access this dataset"
        else:
            return "No dataset with id '%s'" % str( id )

    @web.expose
    def display_child(self, trans, parent_id=None, designation=None, tofile=None, toext=".txt"):
        """Returns child data directly into the browser, based upon parent_id and designation.
        """
        #TODO: unencoded id
        try:
            data = trans.sa_session.query( self.app.model.HistoryDatasetAssociation ).get( parent_id )
            if data:
                child = data.get_child_by_designation( designation )
                if child:
                    current_user_roles = trans.get_current_user_roles()
                    if trans.app.security_agent.can_access_dataset( current_user_roles, child ):
                        return self.display( trans, id=child.id, tofile=tofile, toext=toext )
                    else:
                        return "You are not privileged to access this dataset."
        except Exception:
            pass
        return "A child named %s could not be found for data %s" % ( designation, parent_id )

    @web.expose
    def display_as( self, trans, id=None, display_app=None, **kwd ):
        """Returns a file in a format that can successfully be displayed in display_app.
        """
        #TODO: unencoded id
        data = trans.sa_session.query( self.app.model.HistoryDatasetAssociation ).get( id )
        authz_method = 'rbac'
        if 'authz_method' in kwd:
            authz_method = kwd['authz_method']
        if data:
            current_user_roles = trans.get_current_user_roles()
            if authz_method == 'rbac' and trans.app.security_agent.can_access_dataset( current_user_roles, data ):
                trans.response.set_content_type( data.get_mime() )
                trans.log_event( "Formatted dataset id %s for display at %s" % ( str( id ), display_app ) )
                return data.as_display_type( display_app, **kwd )
            elif authz_method == 'display_at' and trans.app.host_security_agent.allow_action( trans.request.remote_addr,
                                                                                              data.permitted_actions.DATASET_ACCESS,
                                                                                              dataset=data ):
                trans.response.set_content_type( data.get_mime() )
                return data.as_display_type( display_app, **kwd )
            else:
                return "You are not allowed to access this dataset."
        else:
            return "No data with id=%d" % id

    @web.expose
    def peek(self, trans, id=None):
        """Returns a 'peek' at the data.
        """
        #TODO: unused?
        #TODO: unencoded id
        data = trans.sa_session.query( self.app.model.HistoryDatasetAssociation ).get( id )
        if data:
            yield "<html><body><pre>"
            yield data.peek
            yield "</pre></body></html>"
        else:
            yield "No data with id=%d" % id

    ## ---- History management -----------------------------------------------
    @web.expose
    def history_options( self, trans ):
        """Displays a list of history related actions.
        """
        return trans.fill_template( "/history/options.mako",
                                    user=trans.get_user(),
                                    history=trans.get_history( create=True ) )
    @web.expose
    def history_delete( self, trans, id ):
        """Backward compatibility with check_galaxy script.
        """
        #TODO: unused?
        return trans.webapp.controllers['history'].list( trans, id, operation='delete' )

    @web.expose
    def clear_history( self, trans ):
        """Clears the history for a user.
        """
        #TODO: unused? (seems to only be used in TwillTestCase)
        history = trans.get_history()
        for dataset in history.datasets:
            dataset.deleted = True
            dataset.clear_associated_files()
        trans.sa_session.flush()
        trans.log_event( "History id %s cleared" % (str(history.id)) )
        trans.response.send_redirect( url_for("/index" ) )

    @web.expose
    def history_import( self, trans, id=None, confirm=False, **kwd ):
        #TODO: unused?
        #TODO: unencoded id
        user = trans.get_user()
        user_history = trans.get_history()
        if not id:
            return trans.show_error_message( "You must specify a history you want to import.")
        import_history = trans.sa_session.query( trans.app.model.History ).get( id )
        if not import_history:
            return trans.show_error_message( "The specified history does not exist.")
        if user:
            if import_history.user_id == user.id:
                return trans.show_error_message( "You cannot import your own history.")
            new_history = import_history.copy( target_user=trans.user )
            new_history.name = "imported: " + new_history.name
            new_history.user_id = user.id
            galaxy_session = trans.get_galaxy_session()
            try:
                association = trans.sa_session.query( trans.app.model.GalaxySessionToHistoryAssociation ) \
                                              .filter_by( session_id=galaxy_session.id, history_id=new_history.id ) \
                                              .first()
            except:
                association = None
            new_history.add_galaxy_session( galaxy_session, association=association )
            trans.sa_session.add( new_history )
            trans.sa_session.flush()
            if not user_history.datasets:
                trans.set_history( new_history )
            trans.log_event( "History imported, id: %s, name: '%s': " % (str(new_history.id) , new_history.name ) )
            return trans.show_ok_message( """
                History "%s" has been imported. Click <a href="%s">here</a>
                to begin.""" % ( new_history.name, web.url_for( '/' ) ) )
        elif not user_history.datasets or confirm:
            new_history = import_history.copy()
            new_history.name = "imported: " + new_history.name
            new_history.user_id = None
            galaxy_session = trans.get_galaxy_session()
            try:
                association = trans.sa_session.query( trans.app.model.GalaxySessionToHistoryAssociation ) \
                                              .filter_by( session_id=galaxy_session.id, history_id=new_history.id ) \
                                              .first()
            except:
                association = None
            new_history.add_galaxy_session( galaxy_session, association=association )
            trans.sa_session.add( new_history )
            trans.sa_session.flush()
            trans.set_history( new_history )
            trans.log_event( "History imported, id: %s, name: '%s': " % (str(new_history.id) , new_history.name ) )
            return trans.show_ok_message( """
                History "%s" has been imported. Click <a href="%s">here</a>
                to begin.""" % ( new_history.name, web.url_for( '/' ) ) )
        return trans.show_warn_message( """
            Warning! If you import this history, you will lose your current
            history. Click <a href="%s">here</a> to confirm.
            """ % web.url_for( controller='root', action='history_import', id=id, confirm=True ) )

    @web.expose
    def history_new( self, trans, name=None ):
        """Create a new history with the given name
        and refresh the history panel.
        """
        trans.new_history( name=name )
        trans.log_event( "Created new History, id: %s." % str(trans.history.id) )
        return trans.show_message( "New history created", refresh_frames=['history'] )

    @web.expose
    def history_add_to( self, trans, history_id=None, file_data=None,
            name="Data Added to History", info=None, ext="txt", dbkey="?", copy_access_from=None, **kwd ):
        """Adds a POSTed file to a History.
        """
        #TODO: unencoded id
        try:
            history = trans.sa_session.query( trans.app.model.History ).get( history_id )
            data = trans.app.model.HistoryDatasetAssociation( name=name,
                                                              info=info,
                                                              extension=ext,
                                                              dbkey=dbkey,
                                                              create_dataset=True,
                                                              sa_session=trans.sa_session )
            if copy_access_from:
                copy_access_from = trans.sa_session.query( trans.app.model.HistoryDatasetAssociation ).get( copy_access_from )
                trans.app.security_agent.copy_dataset_permissions( copy_access_from.dataset, data.dataset )
            else:
                permissions = trans.app.security_agent.history_get_default_permissions( history )
                trans.app.security_agent.set_all_dataset_permissions( data.dataset, permissions )
            trans.sa_session.add( data )
            trans.sa_session.flush()
            data_file = open( data.file_name, "wb" )
            file_data.file.seek( 0 )
            data_file.write( file_data.file.read() )
            data_file.close()
            data.state = data.states.OK
            data.set_size()
            data.init_meta()
            data.set_meta()
            trans.sa_session.flush()
            history.add_dataset( data )
            trans.sa_session.flush()
            data.set_peek()
            trans.sa_session.flush()
            trans.log_event("Added dataset %d to history %d" % (data.id, trans.history.id))
            return trans.show_ok_message( "Dataset " + str(data.hid) + " added to history " + str(history_id) + "." )
        except Exception, e:
            msg = "Failed to add dataset to history: %s" % ( e )
            log.error( msg )
            trans.log_event( msg )
            return trans.show_error_message("Adding File to History has Failed")

    @web.expose
    def history_set_default_permissions( self, trans, id=None, **kwd ):
        """Sets the permissions on a history.
        """
        #TODO: unencoded id
        if trans.user:
            if 'update_roles_button' in kwd:
                history = None
                if id:
                    try:
                        id = int( id )
                    except:
                        id = None
                    if id:
                        history = trans.sa_session.query( trans.app.model.History ).get( id )
                if not history:
                    # If we haven't retrieved a history, use the current one
                    history = trans.get_history()
                p = Params( kwd )
                permissions = {}
                for k, v in trans.app.model.Dataset.permitted_actions.items():
                    in_roles = p.get( k + '_in', [] )
                    if not isinstance( in_roles, list ):
                        in_roles = [ in_roles ]
                    in_roles = [ trans.sa_session.query( trans.app.model.Role ).get( x ) for x in in_roles ]
                    permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
                dataset = 'dataset' in kwd
                bypass_manage_permission = 'bypass_manage_permission' in kwd
                trans.app.security_agent.history_set_default_permissions( history, permissions,
                    dataset=dataset, bypass_manage_permission=bypass_manage_permission )
                return trans.show_ok_message( 'Default history permissions have been changed.' )
            return trans.fill_template( 'history/permissions.mako' )
        else:
            #user not logged in, history group must be only public
            return trans.show_error_message( "You must be logged in to change a history's default permissions." )

    @web.expose
    def dataset_make_primary( self, trans, id=None):
        """Copies a dataset and makes primary.
        """
        #TODO: unused?
        #TODO: unencoded id
        try:
            old_data = trans.sa_session.query( self.app.model.HistoryDatasetAssociation ).get( id )
            new_data = old_data.copy()
            ## new_data.parent = None
            history = trans.get_history()
            history.add_dataset(new_data)
            trans.sa_session.add( new_data )
            trans.sa_session.flush()
            return trans.show_message( "<p>Secondary dataset has been made primary.</p>", refresh_frames=['history'] )
        except:
            return trans.show_error_message( "<p>Failed to make secondary dataset primary.</p>" )

    @web.expose
    def welcome( self, trans ):
        welcome_url = trans.app.config.welcome_url
        return trans.response.send_redirect( url_for( welcome_url  ) )

    @web.expose
    def bucket_proxy( self, trans, bucket=None, **kwd):
        if bucket:
            trans.response.set_content_type( 'text/xml' )
            b_list_xml = urllib.urlopen('http://s3.amazonaws.com/%s/' % bucket)
            return b_list_xml.read()
        raise Exception("You must specify a bucket")

    # ---- Debug methods ----------------------------------------------------
    @web.expose
    def echo(self, trans, **kwd):
        """Echos parameters (debugging).
        """
        rval = ""
        for k in trans.request.headers:
            rval += "%s: %s <br/>" % ( k, trans.request.headers[k] )
        for k in kwd:
            rval += "%s: %s <br/>" % ( k, kwd[k] )
            if isinstance( kwd[k], cgi.FieldStorage ):
                rval += "-> %s" % kwd[k].file.read()
        return rval

    @web.json
    def echo_json( self, trans, **kwd ):
        """Echos parameters as JSON (debugging).

        Attempts to parse values passed as boolean, float, then int. Defaults
        to string. Non-recursive (will not parse lists).
        """
        #TODO: use json
        rval = {}
        for k in kwd:
            rval[ k ] = kwd[k]
            try:
                if rval[ k ] in [ 'true', 'True', 'false', 'False' ]:
                    rval[ k ] = string_as_bool( rval[ k ] )
                rval[ k ] = float( rval[ k ] )
                rval[ k ] = int( rval[ k ] )
            except:
                pass
        return rval

    @web.expose
    def generate_error( self, trans, code=500 ):
        """Raises an exception (debugging).
        """
        trans.response.status = code
        raise Exception( "Fake error!" )

    @web.json
    def generate_json_error( self, trans, code=500 ):
        """Raises an exception (debugging).
        """
        try:
            code = int( code )
        except Exception, exc:
            code = 500

        if code == 502:
            raise HTTPBadGateway()
        trans.response.status = code
        return { 'error': 'Fake error!' }
