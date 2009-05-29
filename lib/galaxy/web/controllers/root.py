"""
Contains the main interface in the Universe class
"""
import logging, os, sets, string, shutil, urllib, re, socket
from cgi import escape, FieldStorage
from galaxy import util, datatypes, jobs, web, util
from galaxy.web.base.controller import *
from galaxy.model.orm import *

log = logging.getLogger( __name__ )

class RootController( BaseController ):
    
    @web.expose
    def default(self, trans, target1=None, target2=None, **kwd):
        return 'This link may not be followed from within Galaxy.'
    
    @web.expose
    def index(self, trans, id=None, tool_id=None, mode=None, workflow_id=None, m_c=None, m_a=None, **kwd):
        return trans.fill_template( "root/index.mako",
                                    tool_id=tool_id,
                                    workflow_id=workflow_id,
                                    m_c=m_c, m_a=m_a )
        
    ## ---- Tool related -----------------------------------------------------
    
    @web.expose
    def tool_menu( self, trans ):
        if trans.app.config.require_login and not trans.user:
            return trans.fill_template( '/no_access.mako', message = 'Please log in to access Galaxy tools.' )
        else:
            return trans.fill_template('/root/tool_menu.mako', toolbox=self.get_toolbox() )

    @web.expose
    def tool_help( self, trans, id ):
        """Return help page for tool identified by 'id' if available"""
        toolbox = self.get_toolbox()
        tool = toolbox.tools_by_id.get(id, '')
        yield "<html><body>"
        if not tool:
            yield "Unknown tool id '%d'" % id
        elif tool.help:
            yield tool.help
        else:
            yield "No additional help available for tool '%s'" % tool.name
        yield "</body></html>"

    ## ---- Root history display ---------------------------------------------

    @web.expose
    def history( self, trans, as_xml=False, show_deleted=False ):
        """
        Display the current history, creating a new history if neccesary.
        
        NOTE: No longer accepts "id" or "template" options for security reasons.
        """
        history = trans.get_history()
        if trans.app.config.require_login and not trans.user:
            return trans.fill_template( '/no_access.mako', message = 'Please log in to access Galaxy histories.' )
        if as_xml:
            trans.response.set_content_type('text/xml')
            return trans.fill_template_mako( "root/history_as_xml.mako", history=history, show_deleted=util.string_as_bool( show_deleted ) )
        else:
            template = "root/history.mako"
            return trans.fill_template( "root/history.mako", history = history, show_deleted = util.string_as_bool( show_deleted ) )

    @web.expose
    def dataset_state ( self, trans, id=None, stamp=None ):
        if id is not None:
            try: 
                data = self.app.model.HistoryDatasetAssociation.get( id )
            except: 
                return trans.show_error_message( "Unable to check dataset %s." %str( id ) )
            trans.response.headers['X-Dataset-State'] = data.state
            trans.response.headers['Pragma'] = 'no-cache'
            trans.response.headers['Expires'] = '0'
            return data.state
        else:
            return trans.show_error_message( "Must specify a dataset id.")

    @web.expose
    def dataset_code( self, trans, id=None, hid=None, stamp=None ):
        if id is not None:
            try: 
                data = self.app.model.HistoryDatasetAssociation.get( id )
            except: 
                return trans.show_error_message( "Unable to check dataset %s." %str( id ) )
            trans.response.headers['Pragma'] = 'no-cache'
            trans.response.headers['Expires'] = '0'
            return trans.fill_template("root/history_item.mako", data=data, hid=hid)
        else:
            return trans.show_error_message( "Must specify a dataset id.")

    @web.json
    def history_item_updates( self, trans, ids=None, states=None ):
        # Avoid caching
        trans.response.headers['Pragma'] = 'no-cache'
        trans.response.headers['Expires'] = '0'
        # Create new HTML for any that have changed
        rval = {}
        if ids is not None and states is not None:
            ids = map( int, ids.split( "," ) )
            states = states.split( "," )
            for id, state in zip( ids, states ):
                data = self.app.model.HistoryDatasetAssociation.get( id )
                if data.state != state:
                    rval[id] = {
                        "state": data.state,
                        "html": unicode( trans.fill_template( "root/history_item.mako", data=data, hid=data.hid ), 'utf-8' )
                    }
        return rval

    ## ---- Dataset display / editing ----------------------------------------

    @web.expose
    def display( self, trans, id=None, hid=None, tofile=None, toext=".txt", **kwd ):
        """
        Returns data directly into the browser. 
        Sets the mime-type according to the extension
        """
        if hid is not None:
            try:
                hid = int( hid )
            except:
                return "hid '%s' is invalid" %str( hid )
            history = trans.get_history()
            for dataset in history.datasets:
                if dataset.hid == hid:
                    data = dataset
                    break
            else:
                raise Exception( "No dataset with hid '%d'" % hid )
        else:
            try:
                data = self.app.model.HistoryDatasetAssociation.get( id )
            except:
                return "Dataset id '%s' is invalid" %str( id )
        if data:
            if trans.app.security_agent.allow_action( trans.user, data.permitted_actions.DATASET_ACCESS, dataset = data ):
                mime = trans.app.datatypes_registry.get_mimetype_by_extension( data.extension.lower() )
                trans.response.set_content_type(mime)
                if tofile:
                    fStat = os.stat(data.file_name)
                    trans.response.headers['Content-Length'] = int(fStat.st_size)
                    if toext[0:1] != ".":
                        toext = "." + toext
                    valid_chars = '.,^_-()[]0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
                    fname = data.name
                    fname = ''.join(c in valid_chars and c or '_' for c in fname)[0:150]
                    trans.response.headers["Content-Disposition"] = "attachment; filename=GalaxyHistoryItem-%s-[%s]%s" % (data.hid, fname, toext)
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
        """
        Returns child data directly into the browser, based upon parent_id and designation.
        """
        try:
            data = self.app.model.HistoryDatasetAssociation.get( parent_id )
            if data:
                child = data.get_child_by_designation( designation )
                if child:
                    if trans.app.security_agent.allow_action( trans.user, child.permitted_actions.DATASET_ACCESS, dataset = child ):
                        return self.display( trans, id=child.id, tofile=tofile, toext=toext )
                    else:
                        return "You are not privileged to access this dataset."
        except Exception:
            pass
        return "A child named %s could not be found for data %s" % ( designation, parent_id )

    @web.expose
    def display_as( self, trans, id=None, display_app=None, **kwd ):
        """Returns a file in a format that can successfully be displayed in display_app"""
        data = self.app.model.HistoryDatasetAssociation.get( id )
        if data:
            if trans.app.security_agent.allow_action( trans.user, data.permitted_actions.DATASET_ACCESS, dataset = data ):
                trans.response.set_content_type( data.get_mime() )
                trans.log_event( "Formatted dataset id %s for display at %s" % ( str( id ), display_app ) )
                return data.as_display_type( display_app, **kwd )
            else:
                return "You are not privileged to access this dataset."
        else:
            return "No data with id=%d" % id

    @web.expose
    def peek(self, trans, id=None):
        """Returns a 'peek' at the data"""
        data = self.app.model.HistoryDatasetAssociation.get( id )
        if data:
            yield "<html><body><pre>"
            yield data.peek
            yield "</pre></body></html>"
        else:
            yield "No data with id=%d" % id

    @web.expose
    def edit(self, trans, id=None, hid=None, **kwd):
        """Returns data directly into the browser. Sets the mime-type according to the extension"""
        if hid is not None:
            history = trans.get_history()
            # TODO: hid handling
            data = history.datasets[ int( hid ) - 1 ]
        elif id is not None: 
            data = self.app.model.HistoryDatasetAssociation.get( id )
        else:
            trans.log_event( "Problem loading dataset id %s with history id %s." % ( str( id ), str( hid ) ) )
            return trans.show_error_message( "Problem loading dataset." )
        if data is None:
            trans.log_event( "Problem retrieving dataset id %s with history id." % ( str( id ), str( hid ) ) )
            return trans.show_error_message( "Problem retrieving dataset." )
        if id is not None and data.history.user is not None and data.history.user != trans.user:
            return trans.show_error_message( "This instance of a dataset (%s) in a history does not belong to you." % ( data.id ) )
        if trans.app.security_agent.allow_action( trans.user, data.permitted_actions.DATASET_ACCESS, dataset=data ):
            if data.state == trans.model.Dataset.states.UPLOAD:
                return trans.show_error_message( "Please wait until this dataset finishes uploading before attempting to edit its metadata." )
            params = util.Params( kwd, safe=False )
            if params.change:
                # The user clicked the Save button on the 'Change data type' form
                trans.app.datatypes_registry.change_datatype( data, params.datatype )
                trans.app.model.flush()
            elif params.save:
                # The user clicked the Save button on the 'Edit Attributes' form
                data.name  = params.name
                data.info  = params.info
                
                # The following for loop will save all metadata_spec items
                for name, spec in data.datatype.metadata_spec.items():
                    if spec.get("readonly"):
                        continue
                    optional = params.get("is_"+name, None)
                    if optional and optional == 'true':
                        # optional element... == 'true' actually means it is NOT checked (and therefore omitted)
                        setattr(data.metadata, name, None)
                    else:
                        setattr( data.metadata, name, spec.unwrap( params.get (name, None) ) )

                data.datatype.after_edit( data )
                trans.app.model.flush()
                return trans.show_ok_message( "Attributes updated", refresh_frames=['history'] )
            elif params.detect:
                # The user clicked the Auto-detect button on the 'Edit Attributes' form
                for name, spec in data.metadata.spec.items():
                    # We need to be careful about the attributes we are resetting
                    if name not in [ 'name', 'info', 'dbkey' ]:
                        if spec.get( 'default' ):
                            setattr( data.metadata, name, spec.unwrap( spec.get( 'default' ) ) )
                data.set_meta()
                data.datatype.after_edit( data )
                trans.app.model.flush()
                return trans.show_ok_message( "Attributes updated", refresh_frames=['history'] )
            elif params.convert_data:
                target_type = kwd.get("target_type", None)
                if target_type:
                    msg = data.datatype.convert_dataset(trans, data, target_type)
                    return trans.show_ok_message( msg, refresh_frames=['history'] )
            elif params.update_roles_button:
                if not trans.user:
                    return trans.show_error_message( "You must be logged in if you want to change permissions." )
                if trans.app.security_agent.allow_action( trans.user, data.dataset.permitted_actions.DATASET_MANAGE_PERMISSIONS, dataset = data.dataset ):
                    permissions = {}
                    for k, v in trans.app.model.Dataset.permitted_actions.items():
                        in_roles = params.get( k + '_in', [] )
                        if not isinstance( in_roles, list ):
                            in_roles = [ in_roles ]
                        in_roles = [ trans.app.model.Role.get( x ) for x in in_roles ]
                        permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
                    trans.app.security_agent.set_all_dataset_permissions( data.dataset, permissions )
                    data.dataset.refresh()
                else:
                    return trans.show_error_message( "You are not authorized to change this dataset's permissions" )
            data.datatype.before_edit( data )
            
            if "dbkey" in data.datatype.metadata_spec and not data.metadata.dbkey:
                # Copy dbkey into metadata, for backwards compatability
                # This looks like it does nothing, but getting the dbkey
                # returns the metadata dbkey unless it is None, in which
                # case it resorts to the old dbkey.  Setting the dbkey
                # sets it properly in the metadata
                data.metadata.dbkey = data.dbkey
            # let's not overwrite the imported datatypes module with the variable datatypes?
            # the built-in 'id' is overwritten in lots of places as well
            ldatatypes = [x for x in trans.app.datatypes_registry.datatypes_by_extension.iterkeys()]
            ldatatypes.sort()
            trans.log_event( "Opened edit view on dataset %s" % str(id) )
            return trans.fill_template( "/dataset/edit_attributes.mako", data=data, datatypes=ldatatypes )
        else:
            return trans.show_error_message( "You do not have permission to edit this dataset's ( id: %s ) information." % str( id ) )

    def __delete_dataset( self, trans, id ):
        data = self.app.model.HistoryDatasetAssociation.get( id )
        if data:
            # Walk up parent datasets to find the containing history
            topmost_parent = data
            while topmost_parent.parent:
                topmost_parent = topmost_parent.parent
            assert topmost_parent in trans.history.datasets, "Data does not belong to current history"
            # Mark deleted and cleanup
            data.mark_deleted()
            data.clear_associated_files()
            trans.log_event( "Dataset id %s marked as deleted" % str(id) )
            if data.parent_id is None and len( data.creating_job_associations ) > 0:
                # Mark associated job for deletion
                job = data.creating_job_associations[0].job
                if job.state in [ model.Job.states.QUEUED, model.Job.states.RUNNING, model.Job.states.NEW ]:
                    # Are *all* of the job's other output datasets deleted?
                    if job.check_if_output_datasets_deleted():
                        job.mark_deleted()                
                        self.app.job_manager.job_stop_queue.put( job.id )
            self.app.model.flush()

    @web.expose
    def delete( self, trans, id = None, show_deleted_on_refresh = False, **kwd):
        if id:
            if isinstance( id, list ):
                dataset_ids = id
            else:
                dataset_ids = [ id ]
            history = trans.get_history()
            for id in dataset_ids:
                try:
                    id = int( id )
                except:
                    continue
                self.__delete_dataset( trans, id )
        return self.history( trans, show_deleted = show_deleted_on_refresh )
        
    @web.expose
    def delete_async( self, trans, id = None, **kwd):
        if id:
            try:
                id = int( id )
            except:
                return "Dataset id '%s' is invalid" %str( id )
            self.__delete_dataset( trans, id )
        return "OK"

    ## ---- History management -----------------------------------------------

    @web.expose
    def history_options( self, trans ):
        """Displays a list of history related actions"""            
        return trans.fill_template( "/history/options.mako",
                                    user = trans.get_user(), history = trans.get_history() )
        
    @web.expose
    def history_delete( self, trans, id ):
        """
        Backward compatibility with check_galaxy script.
        """
        return trans.webapp.controllers['history'].list( trans, id, operation='delete' )
    
    @web.expose
    def clear_history( self, trans ):
        """Clears the history for a user"""
        history = trans.get_history()
        for dataset in history.datasets:
            dataset.deleted = True
            dataset.clear_associated_files()
        self.app.model.flush()
        trans.log_event( "History id %s cleared" % (str(history.id)) )
        trans.response.send_redirect( url_for("/index" ) )
        
    @web.expose
    def history_import( self, trans, id=None, confirm=False, **kwd ):
        msg = ""
        user = trans.get_user()
        user_history = trans.get_history()
        if not id:
            return trans.show_error_message( "You must specify a history you want to import.")
        import_history = trans.app.model.History.get( id )
        if not import_history:
            return trans.show_error_message( "The specified history does not exist.")
        if user:
            if import_history.user_id == user.id:
                return trans.show_error_message( "You cannot import your own history.")
            new_history = import_history.copy( target_user=trans.user )
            new_history.name = "imported: "+new_history.name
            new_history.user_id = user.id
            galaxy_session = trans.get_galaxy_session()
            try:
                association = trans.app.model.GalaxySessionToHistoryAssociation.filter_by( session_id=galaxy_session.id, history_id=new_history.id ).first()
            except:
                association = None
            new_history.add_galaxy_session( galaxy_session, association=association )
            new_history.flush()
            if not user_history.datasets:
                trans.set_history( new_history )
            trans.log_event( "History imported, id: %s, name: '%s': " % (str(new_history.id) , new_history.name ) )
            return trans.show_ok_message( """
                History "%s" has been imported. Click <a href="%s">here</a>
                to begin.""" % ( new_history.name, web.url_for( '/' ) ) )
        elif not user_history.datasets or confirm:
            new_history = import_history.copy()
            new_history.name = "imported: "+new_history.name
            new_history.user_id = None
            galaxy_session = trans.get_galaxy_session()
            try:
                association = trans.app.model.GalaxySessionToHistoryAssociation.filter_by( session_id=galaxy_session.id, history_id=new_history.id ).first()
            except:
                association = None
            new_history.add_galaxy_session( galaxy_session, association=association )
            new_history.flush()
            trans.set_history( new_history )
            trans.log_event( "History imported, id: %s, name: '%s': " % (str(new_history.id) , new_history.name ) )
            return trans.show_ok_message( """
                History "%s" has been imported. Click <a href="%s">here</a>
                to begin.""" % ( new_history.name, web.url_for( '/' ) ) )
        return trans.show_warn_message( """
            Warning! If you import this history, you will lose your current
            history. Click <a href="%s">here</a> to confirm.
            """ % web.url_for( id=id, confirm=True ) )
                
    @web.expose
    def history_new( self, trans ):
        trans.new_history()
        trans.log_event( "Created new History, id: %s." % str(trans.get_history().id) )
        return trans.show_message( "New history created", refresh_frames = ['history'] )

    @web.expose
    def history_add_to( self, trans, history_id=None, file_data=None, name="Data Added to History",info=None,ext="txt",dbkey="?",copy_access_from=None,**kwd ):
        """Adds a POSTed file to a History"""
        try:
            history = trans.app.model.History.get( history_id )
            data = trans.app.model.HistoryDatasetAssociation( name = name, info = info, extension = ext, dbkey = dbkey, create_dataset = True )
            if copy_access_from:
                copy_access_from = trans.app.model.HistoryDatasetAssociation.get( copy_access_from )
                trans.app.security_agent.copy_dataset_permissions( copy_access_from.dataset, data.dataset )
            else:
                permissions = trans.app.security_agent.history_get_default_permissions( history )
                trans.app.security_agent.set_all_dataset_permissions( data.dataset, permissions )
            data.flush()
            data_file = open( data.file_name, "wb" )
            file_data.file.seek( 0 )
            data_file.write( file_data.file.read() )
            data_file.close()
            data.state = data.states.OK
            data.set_size()
            data.init_meta()
            data.set_meta()
            data.flush()
            history.add_dataset( data )
            history.flush()
            data.set_peek()
            data.flush()
            trans.log_event("Added dataset %d to history %d" %(data.id, trans.history.id))
            return trans.show_ok_message("Dataset "+str(data.hid)+" added to history "+str(history_id)+".")
        except Exception, e:
            trans.log_event( "Failed to add dataset to history: %s" % ( e ) )
            return trans.show_error_message("Adding File to History has Failed")

    @web.expose
    def history_set_default_permissions( self, trans, **kwd ):
        """Sets the user's default permissions for the current history"""
        if trans.user:
            if 'update_roles_button' in kwd:
                history = trans.get_history()
                p = util.Params( kwd )
                permissions = {}
                for k, v in trans.app.model.Dataset.permitted_actions.items():
                    in_roles = p.get( k + '_in', [] )
                    if not isinstance( in_roles, list ):
                        in_roles = [ in_roles ]
                    in_roles = [ trans.app.model.Role.get( x ) for x in in_roles ]
                    permissions[ trans.app.security_agent.get_action( v.action ) ] = in_roles
                dataset = 'dataset' in kwd
                bypass_manage_permission = 'bypass_manage_permission' in kwd
                trans.app.security_agent.history_set_default_permissions( history, permissions, dataset=dataset, bypass_manage_permission=bypass_manage_permission )
                return trans.show_ok_message( 'Default history permissions have been changed.' )
            return trans.fill_template( 'history/permissions.mako' )
        else:
            #user not logged in, history group must be only public
            return trans.show_error_message( "You must be logged in to change a history's default permissions." )

    @web.expose
    def dataset_make_primary( self, trans, id=None):
        """Copies a dataset and makes primary"""
        try:
            old_data = self.app.model.HistoryDatasetAssociation.get( id )
            new_data = old_data.copy()
            ## new_data.parent = None
            ## history = trans.app.model.History.get( old_data.history_id )
            history = trans.get_history()
            history.add_dataset(new_data)
            new_data.flush()
            return trans.show_message( "<p>Secondary dataset has been made primary.</p>", refresh_frames=['history'] ) 
        except:
            return trans.show_error_message( "<p>Failed to make secondary dataset primary.</p>" ) 

    # @web.expose
    # def masthead( self, trans, active_view=None ):
    #     brand = trans.app.config.get( "brand", "" )
    #     if brand:
    #         brand ="<span class='brand'>/%s</span>" % brand
    #     wiki_url = trans.app.config.get( "wiki_url", "http://g2.trac.bx.psu.edu/" )
    #     bugs_email = trans.app.config.get( "bugs_email", "mailto:galaxy-bugs@bx.psu.edu"  )
    #     blog_url = trans.app.config.get( "blog_url", "http://g2.trac.bx.psu.edu/blog"   )
    #     screencasts_url = trans.app.config.get( "screencasts_url", "http://g2.trac.bx.psu.edu/wiki/ScreenCasts" )
    #     admin_user = "false"
    #     admin_users = trans.app.config.get( "admin_users", "" ).split( "," )
    #     user = trans.get_user()
    #     if user:
    #         user_email = trans.get_user().email
    #         if user_email in admin_users:
    #             admin_user = "true"
    #     return trans.fill_template( "/root/masthead.mako", brand=brand, wiki_url=wiki_url, 
    #       blog_url=blog_url,bugs_email=bugs_email, screencasts_url=screencasts_url, admin_user=admin_user, active_view=active_view )

    @web.expose
    def dataset_errors( self, trans, id=None, **kwd ):
        """View/fix errors associated with dataset"""
        data = trans.app.model.HistoryDatasetAssociation.get( id )
        p = kwd
        if p.get("fix_errors", None):
            # launch tool to create new, (hopefully) error free dataset
            tool_params = {}
            tool_params["tool_id"] = 'fix_errors'
            tool_params["runtool_btn"] = 'T'
            tool_params["input"] = id
            tool_params["ext"] = data.ext
            # send methods selected
            repair_methods = data.datatype.repair_methods( data )
            methods = []
            for method, description in repair_methods:
                if method in p: methods.append(method)
            tool_params["methods"] = ",".join(methods)
            url = "/tool_runner/index?" + urllib.urlencode(tool_params)
            trans.response.send_redirect(url)                
        else:
            history = trans.app.model.History.get( data.history_id )
            return trans.fill_template('dataset/validation.tmpl', data=data, history=history)

    # ---- Debug methods ----------------------------------------------------

    @web.expose
    def echo(self, trans, **kwd):
        """Echos parameters (debugging)"""
        rval = ""
        for k in trans.request.headers:
            rval += "%s: %s <br/>" % ( k, trans.request.headers[k] )
        for k in kwd:
            rval += "%s: %s <br/>" % ( k, kwd[k] )
            if isinstance( kwd[k], FieldStorage ):
                rval += "-> %s" % kwd[k].file.read()
        return rval
    
    @web.expose
    def generate_error( self, trans ):
        raise Exception( "Fake error!" )




