"""
Contains the main interface in the Universe class
"""
import logging, os, string, shutil, urllib, re, socket
from cgi import escape, FieldStorage
from galaxy import util, datatypes, jobs, web, util
from galaxy.web.base.controller import *
from galaxy.util.sanitize_html import sanitize_html
from galaxy.model.orm import *
from galaxy.model.item_attrs import UsesAnnotations

log = logging.getLogger( __name__ )

class RootController( BaseController, UsesHistory, UsesAnnotations ):
    
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
            ## Get most recently used tools.
            toolbox = self.get_toolbox()
            recent_tools = []
            if trans.user:
                for row in trans.sa_session.query( self.app.model.Job.tool_id ). \
                                                            filter( self.app.model.Job.user==trans.user ). \
                                                            order_by( self.app.model.Job.create_time.desc() ):
                    tool_id = row[0]
                    a_tool = toolbox.tools_by_id.get( tool_id, None )
                    if a_tool and not a_tool.hidden and a_tool not in recent_tools:
                        recent_tools.append( a_tool )
                        ## TODO: make number of recently used tools a user preference.
                        if len ( recent_tools ) == 5:
                            break
                        
            return trans.fill_template('/root/tool_menu.mako', toolbox=toolbox, recent_tools=recent_tools )

    @web.json
    def tool_search( self, trans, **kwd ):
        query = kwd.get( 'query', '' )
        tags = util.listify( kwd.get( 'tags[]', [] ) )
        trans.log_action( trans.get_user(), "tool_search.search", "", { "query" : query, "tags" : tags } )
        results = []
        if tags:
            tags = trans.sa_session.query( trans.app.model.Tag ).filter( trans.app.model.Tag.name.in_( tags ) ).all()
            for tagged_tool_il in [ tag.tagged_tools for tag in tags ]:
                for tagged_tool in tagged_tool_il:
                    if tagged_tool.tool_id not in results:
                        results.append( tagged_tool.tool_id )
        if len( query ) > 3:
            search_results = trans.app.toolbox_search.search( query )
            if 'tags[]' in kwd:
                results = filter( lambda x: x in results, search_results )
            else:
                results = search_results
        return results

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
    def my_data( self, trans, **kwd ):
        """
        Display user's data.
        """
        return trans.fill_template_mako( "/my_data.mako" )

    @web.expose
    def history( self, trans, as_xml=False, show_deleted=False, show_hidden=False, hda_id=None ):
        """
        Display the current history, creating a new history if necessary.
        NOTE: No longer accepts "id" or "template" options for security reasons.
        """
        if trans.app.config.require_login and not trans.user:
            return trans.fill_template( '/no_access.mako', message = 'Please log in to access Galaxy histories.' )
        history = trans.get_history( create=True )
        if as_xml:
            trans.response.set_content_type('text/xml')
            return trans.fill_template_mako( "root/history_as_xml.mako", 
                                              history=history, 
                                              show_deleted=util.string_as_bool( show_deleted ),
                                              show_hidden=util.string_as_bool( show_hidden ) )
        else:
            show_deleted = util.string_as_bool( show_deleted )
            show_hidden = util.string_as_bool( show_hidden )
            datasets = self.get_history_datasets( trans, history, show_deleted, show_hidden )
            return trans.stream_template_mako( "root/history.mako",
                                               history = history,
                                               annotation = self.get_item_annotation_str( trans.sa_session, trans.user, history ),
                                               datasets = datasets,
                                               hda_id = hda_id,
                                               show_deleted = show_deleted,
                                               show_hidden=show_hidden )

    @web.expose
    def dataset_state ( self, trans, id=None, stamp=None ):
        if id is not None:
            try: 
                data = trans.sa_session.query( self.app.model.HistoryDatasetAssociation ).get( id )
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
                data = trans.sa_session.query( self.app.model.HistoryDatasetAssociation ).get( id )
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
                data = trans.sa_session.query( self.app.model.HistoryDatasetAssociation ).get( id )
                if data.state != state:
                    job_hda = data
                    while job_hda.copied_from_history_dataset_association:
                        job_hda = job_hda.copied_from_history_dataset_association
                    force_history_refresh = False
                    if job_hda.creating_job_associations:
                        tool = trans.app.toolbox.tools_by_id.get( job_hda.creating_job_associations[ 0 ].job.tool_id, None )
                        if tool:
                            force_history_refresh = tool.force_history_refresh
                    if not job_hda.visible:
                        force_history_refresh = True 
                    rval[id] = {
                        "state": data.state,
                        "html": unicode( trans.fill_template( "root/history_item.mako", data=data, hid=data.hid ), 'utf-8' ),
                        "force_history_refresh": force_history_refresh
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
            current_user_roles = trans.get_current_user_roles()
            if trans.app.security_agent.can_access_dataset( current_user_roles, data.dataset ):
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
        """Returns a file in a format that can successfully be displayed in display_app"""
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
                                                                                              dataset = data ):
                trans.response.set_content_type( data.get_mime() )
                return data.as_display_type( display_app, **kwd )
            else:
                return "You are not allowed to access this dataset."
        else:
            return "No data with id=%d" % id

    @web.expose
    def peek(self, trans, id=None):
        """Returns a 'peek' at the data"""
        data = trans.sa_session.query( self.app.model.HistoryDatasetAssociation ).get( id )
        if data:
            yield "<html><body><pre>"
            yield data.peek
            yield "</pre></body></html>"
        else:
            yield "No data with id=%d" % id

    @web.expose
    def edit(self, trans, id=None, hid=None, **kwd):
        """Allows user to modify parameters of an HDA."""
        message = ''
        error = False
        def __ok_to_edit_metadata( dataset_id ):
            #prevent modifying metadata when dataset is queued or running as input/output
            #This code could be more efficient, i.e. by using mappers, but to prevent slowing down loading a History panel, we'll leave the code here for now
            for job_to_dataset_association in trans.sa_session.query( self.app.model.JobToInputDatasetAssociation ) \
                                                              .filter_by( dataset_id=dataset_id ) \
                                                              .all() \
                                            + trans.sa_session.query( self.app.model.JobToOutputDatasetAssociation ) \
                                                              .filter_by( dataset_id=dataset_id ) \
                                                              .all():
                if job_to_dataset_association.job.state not in [ job_to_dataset_association.job.states.OK, job_to_dataset_association.job.states.ERROR, job_to_dataset_association.job.states.DELETED ]:
                    return False
            return True
        if hid is not None:
            history = trans.get_history()
            # TODO: hid handling
            data = history.datasets[ int( hid ) - 1 ]
        elif id is not None: 
            data = trans.sa_session.query( self.app.model.HistoryDatasetAssociation ).get( id )
        else:
            trans.log_event( "Problem loading dataset id %s with history id %s." % ( str( id ), str( hid ) ) )
            return trans.show_error_message( "Problem loading dataset." )
        if data is None:
            trans.log_event( "Problem retrieving dataset id %s with history id." % ( str( id ), str( hid ) ) )
            return trans.show_error_message( "Problem retrieving dataset." )
        if id is not None and data.history.user is not None and data.history.user != trans.user:
            return trans.show_error_message( "This instance of a dataset (%s) in a history does not belong to you." % ( data.id ) )
        current_user_roles = trans.get_current_user_roles()
        if trans.app.security_agent.can_access_dataset( current_user_roles, data.dataset ):
            if data.state == trans.model.Dataset.states.UPLOAD:
                return trans.show_error_message( "Please wait until this dataset finishes uploading before attempting to edit its metadata." )
            params = util.Params( kwd, sanitize=False )
            if params.change:
                # The user clicked the Save button on the 'Change data type' form
                if data.datatype.allow_datatype_change and trans.app.datatypes_registry.get_datatype_by_extension( params.datatype ).allow_datatype_change:
                    #prevent modifying datatype when dataset is queued or running as input/output
                    if not __ok_to_edit_metadata( data.id ):
                        return trans.show_error_message( "This dataset is currently being used as input or output.  You cannot change datatype until the jobs have completed or you have canceled them." )
                    trans.app.datatypes_registry.change_datatype( data, params.datatype, set_meta = not trans.app.config.set_metadata_externally )
                    trans.sa_session.flush()
                    if trans.app.config.set_metadata_externally:
                        trans.app.datatypes_registry.set_external_metadata_tool.tool_action.execute( trans.app.datatypes_registry.set_external_metadata_tool, trans, incoming = { 'input1':data }, overwrite = False ) #overwrite is False as per existing behavior
                    return trans.show_ok_message( "Changed the type of dataset '%s' to %s" % ( data.name, params.datatype ), refresh_frames=['history'] )
                else:
                    return trans.show_error_message( "You are unable to change datatypes in this manner. Changing %s to %s is not allowed." % ( data.extension, params.datatype ) )
            elif params.save:
                # The user clicked the Save button on the 'Edit Attributes' form
                data.name  = params.name
                data.info  = params.info
                message = ''
                if __ok_to_edit_metadata( data.id ):
                    # The following for loop will save all metadata_spec items
                    for name, spec in data.datatype.metadata_spec.items():
                        if spec.get("readonly"):
                            continue
                        optional = params.get("is_"+name, None)
                        other = params.get("or_"+name, None)
                        if optional and optional == 'true':
                            # optional element... == 'true' actually means it is NOT checked (and therefore omitted)
                            setattr(data.metadata, name, None)
                        else:
                            if other:
                                setattr( data.metadata, name, other )
                            else:
                                setattr( data.metadata, name, spec.unwrap( params.get (name, None) ) )
                    data.datatype.after_setting_metadata( data )
                    # Sanitize annotation before adding it.
                    if params.annotation:
                        annotation = sanitize_html( params.annotation, 'utf-8', 'text/html' )
                        self.add_item_annotation( trans.sa_session, trans.get_user(), data, annotation )
                    # If setting metadata previously failed and all required elements have now been set, clear the failed state.
                    if data._state == trans.model.Dataset.states.FAILED_METADATA and not data.missing_meta():
                        data._state = None
                    trans.sa_session.flush()
                    return trans.show_ok_message( "Attributes updated%s" % message, refresh_frames=['history'] )
                else:
                    trans.sa_session.flush()
                    return trans.show_warn_message( "Attributes updated, but metadata could not be changed because this dataset is currently being used as input or output. You must cancel or wait for these jobs to complete before changing metadata.", refresh_frames=['history'] )
            elif params.detect:
                # The user clicked the Auto-detect button on the 'Edit Attributes' form
                #prevent modifying metadata when dataset is queued or running as input/output
                if not __ok_to_edit_metadata( data.id ):
                    return trans.show_error_message( "This dataset is currently being used as input or output.  You cannot change metadata until the jobs have completed or you have canceled them." )
                for name, spec in data.metadata.spec.items():
                    # We need to be careful about the attributes we are resetting
                    if name not in [ 'name', 'info', 'dbkey', 'base_name' ]:
                        if spec.get( 'default' ):
                            setattr( data.metadata, name, spec.unwrap( spec.get( 'default' ) ) )
                if trans.app.config.set_metadata_externally:
                    message = 'Attributes have been queued to be updated'
                    trans.app.datatypes_registry.set_external_metadata_tool.tool_action.execute( trans.app.datatypes_registry.set_external_metadata_tool, trans, incoming = { 'input1':data } )
                else:
                    message = 'Attributes updated'
                    data.set_meta()
                    data.datatype.after_setting_metadata( data )
                trans.sa_session.flush()
                return trans.show_ok_message( message, refresh_frames=['history'] )
            elif params.convert_data:
                target_type = kwd.get("target_type", None)
                if target_type:
                    message = data.datatype.convert_dataset(trans, data, target_type)
                    return trans.show_ok_message( message, refresh_frames=['history'] )
            elif params.update_roles_button:
                if not trans.user:
                    return trans.show_error_message( "You must be logged in if you want to change permissions." )
                if trans.app.security_agent.can_manage_dataset( current_user_roles, data.dataset ):
                    # The user associated the DATASET_ACCESS permission on the dataset with 1 or more roles.  We
                    # need to ensure that they did not associate roles that would cause accessibility problems.
                    permissions, in_roles, error, message = \
                    trans.app.security_agent.derive_roles_from_access( trans, data.dataset.id, 'root', **kwd )
                    a = trans.app.security_agent.get_action( trans.app.security_agent.permitted_actions.DATASET_ACCESS.action )
                    if error:
                        # Keep the original role associations for the DATASET_ACCESS permission on the dataset.
                        permissions[ a ] = data.dataset.get_access_roles( trans )
                    trans.app.security_agent.set_all_dataset_permissions( data.dataset, permissions )
                    trans.sa_session.refresh( data.dataset )
                    if not message:
                        message = 'Your changes completed successfully.'
                else:
                    return trans.show_error_message( "You are not authorized to change this dataset's permissions" )
            if "dbkey" in data.datatype.metadata_spec and not data.metadata.dbkey:
                # Copy dbkey into metadata, for backwards compatability
                # This looks like it does nothing, but getting the dbkey
                # returns the metadata dbkey unless it is None, in which
                # case it resorts to the old dbkey.  Setting the dbkey
                # sets it properly in the metadata
                #### This is likely no longer required, since the dbkey exists entirely within metadata (the old_dbkey field is gone): REMOVE ME?
                data.metadata.dbkey = data.dbkey
            # let's not overwrite the imported datatypes module with the variable datatypes?
            # the built-in 'id' is overwritten in lots of places as well
            ldatatypes = [ dtype_name for dtype_name, dtype_value in trans.app.datatypes_registry.datatypes_by_extension.iteritems() if dtype_value.allow_datatype_change ]
            ldatatypes.sort()
            all_roles = trans.app.security_agent.get_legitimate_roles( trans, data.dataset, 'root' )
            if error:
                status = 'error'
            else:
                status = 'done'
            return trans.fill_template( "/dataset/edit_attributes.mako",
                                        data=data,
                                        data_annotation=self.get_item_annotation_str( trans.sa_session, trans.user, data ),
                                        datatypes=ldatatypes,
                                        current_user_roles=current_user_roles,
                                        all_roles=all_roles,
                                        message=message,
                                        status=status )
        else:
            return trans.show_error_message( "You do not have permission to edit this dataset's ( id: %s ) information." % str( id ) )

    def __delete_dataset( self, trans, id ):
        data = trans.sa_session.query( self.app.model.HistoryDatasetAssociation ).get( id )
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
                if job.state in [ self.app.model.Job.states.QUEUED, self.app.model.Job.states.RUNNING, self.app.model.Job.states.NEW ]:
                    # Are *all* of the job's other output datasets deleted?
                    if job.check_if_output_datasets_deleted():
                        job.mark_deleted( self.app.config.get_bool( 'enable_job_running', True ),
                                          self.app.config.get_bool( 'track_jobs_in_database', False ) )
                        self.app.job_manager.job_stop_queue.put( job.id )
            trans.sa_session.flush()

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
                                    user=trans.get_user(),
                                    history=trans.get_history( create=True ) )
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
        trans.sa_session.flush()
        trans.log_event( "History id %s cleared" % (str(history.id)) )
        trans.response.send_redirect( url_for("/index" ) )
    @web.expose
    def history_import( self, trans, id=None, confirm=False, **kwd ):
        msg = ""
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
            new_history.name = "imported: "+new_history.name
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
            new_history.name = "imported: "+new_history.name
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
            """ % web.url_for( id=id, confirm=True ) )
    @web.expose
    def history_new( self, trans, name=None ):
        trans.new_history( name=name )
        trans.log_event( "Created new History, id: %s." % str(trans.history.id) )
        return trans.show_message( "New history created", refresh_frames = ['history'] )
    @web.expose
    def history_add_to( self, trans, history_id=None, file_data=None, name="Data Added to History",info=None,ext="txt",dbkey="?",copy_access_from=None,**kwd ):
        """Adds a POSTed file to a History"""
        try:
            history = trans.sa_session.query( trans.app.model.History ).get( history_id )
            data = trans.app.model.HistoryDatasetAssociation( name = name,
                                                              info = info,
                                                              extension = ext,
                                                              dbkey = dbkey,
                                                              create_dataset = True,
                                                              sa_session = trans.sa_session )
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
            trans.log_event("Added dataset %d to history %d" %(data.id, trans.history.id))
            return trans.show_ok_message("Dataset "+str(data.hid)+" added to history "+str(history_id)+".")
        except Exception, e:
            trans.log_event( "Failed to add dataset to history: %s" % ( e ) )
            return trans.show_error_message("Adding File to History has Failed")
    @web.expose
    def history_set_default_permissions( self, trans, id=None, **kwd ):
        """Sets the permissions on a history"""
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
                p = util.Params( kwd )
                permissions = {}
                for k, v in trans.app.model.Dataset.permitted_actions.items():
                    in_roles = p.get( k + '_in', [] )
                    if not isinstance( in_roles, list ):
                        in_roles = [ in_roles ]
                    in_roles = [ trans.sa_session.query( trans.app.model.Role ).get( x ) for x in in_roles ]
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
            old_data = trans.sa_session.query( self.app.model.HistoryDatasetAssociation ).get( id )
            new_data = old_data.copy()
            ## new_data.parent = None
            ## history = trans.app.model.History.get( old_data.history_id )
            history = trans.get_history()
            history.add_dataset(new_data)
            trans.sa_session.add( new_data )
            trans.sa_session.flush()
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

    # @web.expose
    # def dataset_errors( self, trans, id=None, **kwd ):
    #     """View/fix errors associated with dataset"""
    #     data = trans.app.model.HistoryDatasetAssociation.get( id )
    #     p = kwd
    #     if p.get("fix_errors", None):
    #         # launch tool to create new, (hopefully) error free dataset
    #         tool_params = {}
    #         tool_params["tool_id"] = 'fix_errors'
    #         tool_params["runtool_btn"] = 'T'
    #         tool_params["input"] = id
    #         tool_params["ext"] = data.ext
    #         # send methods selected
    #         repair_methods = data.datatype.repair_methods( data )
    #         methods = []
    #         for method, description in repair_methods:
    #             if method in p: methods.append(method)
    #         tool_params["methods"] = ",".join(methods)
    #         url = "/tool_runner/index?" + urllib.urlencode(tool_params)
    #         trans.response.send_redirect(url)                
    #     else:
    #         history = trans.app.model.History.get( data.history_id )
    #         return trans.fill_template('dataset/validation.tmpl', data=data, history=history)

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
