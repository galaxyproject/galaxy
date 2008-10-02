"""
Contains the main interface in the Universe class
"""
from galaxy.web.base.controller import *

import logging, os, sets, string, shutil
import re, socket

from galaxy import util, datatypes, jobs, web, util

from cgi import escape, FieldStorage
import urllib

log = logging.getLogger( __name__ )

class RootController( BaseController ):
    
    @web.expose
    def default(self, trans, target1=None, target2=None, **kwd):
        return 'This link may not be followed from within Galaxy.'
    
    @web.expose
    def index(self, trans, id=None, tool_id=None, mode=None, m_c=None, m_a=None, **kwd):
        return trans.fill_template( "root/index.mako", tool_id=tool_id, m_c=m_c, m_a=m_a )
        
    ## ---- Tool related -----------------------------------------------------
    
    @web.expose
    def tool_menu( self, trans ):
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
    def history( self, trans, as_xml=False ):
        """
        Display the current history, creating a new history if neccesary.
        
        NOTE: No longer accepts "id" or "template" options for security reasons.
        """
        try:
            history = trans.get_history()
        except:
            return self.history_new(trans)
        if as_xml:
            trans.response.set_content_type('text/xml')
            return trans.fill_template_mako( "root/history_as_xml.mako", history=history )
        else:
            template = "root/history.mako"
            return trans.fill_template( "root/history.mako", history=history )

    @web.expose
    def dataset_state ( self, trans, id=None, stamp=None ):
        if id is not None:
            try:
                data = self.app.model.Dataset.get( id )
            except: 
                return trans.show_error_message( "Unable to check dataset id %s." %str( id ) )
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
                hda = self.app.model.HistoryDatasetAssociation.filter_by( dataset_id=id ).first()
            except: 
                return trans.show_error_message( "Unable to check dataset id %s." % str( id ) )
            trans.response.headers['Pragma'] = 'no-cache'
            trans.response.headers['Expires'] = '0'
            return trans.fill_template( "root/history_item.mako", data=hda.dataset, hid=hid )
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
                hda = self.app.model.HistoryDatasetAssociation.filter_by( dataset_id=id ).first()
                if hda.dataset.state != state:
                    rval[id] = {
                        "state": hda.dataset.state,
                        "html": trans.fill_template( "root/history_item.mako", data=hda, hid=hda.hid )
                    }
        return rval

    ## ---- Dataset display / editing ----------------------------------------

    @web.expose
    def display(self, trans, id=None, hid=None, tofile=None, toext=".txt"):
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
            for hda in history.datasets:
                if hda.hid == hid:
                    history_dataset_assoc = hda
                    break
            else:
                raise Exception( "History_dataset_association with hid '%s' does not exist." % str( hid ) )
        else:
            try:
                history_dataset_assoc = self.app.model.HistoryDatasetAssociation.filter_by( dataset_id=id ).first()
            except:
                return "Dataset id '%s' is invalid." %str( id )
        if history_dataset_assoc:
            mime = trans.app.datatypes_registry.get_mimetype_by_extension( history_dataset_assoc.extension.lower() )
            trans.response.set_content_type(mime)
            if tofile:
                fStat = os.stat(history_dataset_assoc.file_name)
                trans.response.headers['Content-Length'] = int(fStat.st_size)
                if toext[0:1] != ".":
                    toext = "." + toext
                valid_chars = '.,^_-()[]0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
                fname = history_dataset_assoc.name
                fname = ''.join(c in valid_chars and c or '_' for c in fname)[0:150]
                trans.response.headers["Content-Disposition"] = "attachment; filename=GalaxyHistoryItem-%s-[%s]%s" % (history_dataset_assoc.hid, fname, toext)
            trans.log_event( "Display dataset id: '%s'." % str(id) )
            try:
                return open( history_dataset_assoc.file_name )
            except: 
                return "Dataset id '%s' contains no content." % str( id )
        else:
            return "Dataset id '%s' does not exist." % str( id )

    @web.expose
    def display_child(self, trans, parent_id=None, designation=None, tofile=None, toext=".txt"):
        """
        Returns child data directly into the browser, based upon parent_id and designation.
        """
        try:
            hda = self.app.model.HistoryDatasetAssociation.get( parent_id )
            if hda:
                child = hda.get_child_by_designation( designation )
                if child:
                    return self.display(trans, id=child.id, tofile=tofile, toext=toext)
        except Exception:
            pass
        return "A child named '%s' could not be found for history_dataset_association id '%s'" % ( designation, str( parent_id ) )

    @web.expose
    def display_as( self, trans, id=None, display_app=None, **kwd ):
        """Returns a file in a format that can successfully be displayed in display_app"""
        hda = self.app.model.HistoryDatasetAssociation.filter_by( dataset_id=id ).first()
        if hda:
            trans.response.set_content_type( hda.get_mime() )
            trans.log_event( "Formatted dataset id %s for display at %s" % ( str(id), display_app ) )
            return hda.as_display_type( display_app, **kwd )
        else:
            return "Dataset 'id' %s does not exist." % str( id )

    @web.expose
    def peek(self, trans, id=None):
        """Returns a 'peek' at the data"""
        hda = self.app.model.HistoryDatasetAssociation.filter_by( dataset_id=id ).first()
        if hda:
            yield "<html><body><pre>"
            yield hda.peek
            yield "</pre></body></html>"
        else:
            yield "Dataset 'id' %s does not exist." % str( id )

    @web.expose
    def edit(self, trans, id=None, hid=None, **kwd):
        """Returns data directly into the browser. Sets the mime-type according to the extension"""
        if hid is not None:
            history = trans.get_history()
            # TODO: hid handling
            hda = history.datasets[ int( hid ) - 1 ]
        elif id is None: 
            return trans.show_error_message( "Problem loading dataset id '%s' with history id '%s'." % ( str( id ), str( hid ) ) )
        else:
            hda = self.app.model.HistoryDatasetAssociation.filter_by( dataset_id=id ).first()
        if hda is None:
            return trans.show_error_message( "Problem retrieving dataset 'id' %s with history id '%s'." % ( str( id ), str( hid ) ) )

        p = util.Params(kwd, safe=False)
        
        if p.change:
            # The user clicked the Save button on the 'Change data type' form
            trans.app.datatypes_registry.change_datatype( hda, p.datatype )
            trans.app.model.flush()
        elif p.save:
            # The user clicked the Save button on the 'Edit Attributes' form
            hda.name  = p.name
            hda.info  = p.info
            
            # The following for loop will save all metadata_spec items
            for name, spec in hda.datatype.metadata_spec.items():
                if spec.get("readonly"):
                    continue
                optional = p.get("is_"+name, None)
                if optional and optional == 'true':
                    # optional element... == 'true' actually means it is NOT checked (and therefore ommitted)
                    setattr( hda.metadata, name, None )
                else:
                    setattr( hda.metadata, name, spec.unwrap( p.get( name, None ), p ) )

            hda.datatype.after_edit( hda )
            trans.app.model.flush()
            return trans.show_ok_message( "Attributes updated", refresh_frames=['history'] )
        elif p.detect:
            # The user clicked the Auto-detect button on the 'Edit Attributes' form
            for name, spec in hda.datatype.metadata_spec.items():
                # We need to be careful about the attributes we are resetting
                if name != 'name' and name != 'info' and name != 'dbkey':
                    if spec.get( 'default' ):
                        setattr( hda.metadata, name, spec.unwrap( spec.get( 'default' ), spec ) )
            hda.datatype.set_meta( hda )
            hda.datatype.after_edit( hda )
            trans.app.model.flush()
            return trans.show_ok_message( "Attributes updated", refresh_frames=['history'] )
        elif p.convert_data:
            """The user clicked the Convert button on the 'Convert to new format' form"""
            target_type = kwd.get("target_type", None)
            if target_type:
                msg = hda.datatype.convert_dataset(trans, hda, target_type)
                return trans.show_ok_message( msg, refresh_frames=['history'] )
        hda.datatype.before_edit( hda )
        
        if "dbkey" in hda.datatype.metadata_spec and not hda.metadata.dbkey:
            # Copy dbkey into metadata, for backwards compatability
            # This looks like it does nothing, but getting the dbkey
            # returns the metadata dbkey unless it is None, in which
            # case it resorts to the old dbkey.  Setting the dbkey
            # sets it properly in the metadata
            hda.metadata.dbkey = hda.dbkey
        metadata = list()
        # a list of MetadataParemeters
        for name, spec in hda.datatype.metadata_spec.items():
            if spec.visible:
                metadata.append( spec.wrap( hda.metadata.get( name ), hda ) )
        # let's not overwrite the imported datatypes module with the variable datatypes?
        ldatatypes = [x for x in trans.app.datatypes_registry.datatypes_by_extension.iterkeys()]
        ldatatypes.sort()
        trans.log_event( "Opened edit view on dataset id '%s'" % str( id ) )
        return trans.fill_template( "/dataset/edit_attributes.mako", data=hda, metadata=metadata, datatypes=ldatatypes, err=None )

    @web.expose
    def delete( self, trans, id = None, **kwd):
        if id:
            if isinstance( id, list ):
                dataset_ids = id
            else:
                dataset_ids = [ id ]
            history = trans.get_history()
            for id in dataset_ids:
                try:
                    int( id )
                except:
                    continue
                hda = self.app.model.HistoryDatasetAssociation.filter_by( dataset_id=id ).first()
                if hda:
                    # Walk up parent hdas to find the containing history
                    topmost_parent = hda
                    while topmost_parent.parent:
                        topmost_parent = topmost_parent.parent
                    assert topmost_parent in history.datasets, "Data does not belong to current history"
                    # Mark deleted and cleanup
                    hda.mark_deleted()
                    hda.clear_associated_files()
                    self.app.model.flush()
                    trans.log_event( "Dataset id '%s' marked as deleted" % str( id ) )
                    if hda.parent_id is None:
                        try:
                            self.app.job_stop_queue.put( hda.creating_job_associations[0].job )
                        except IndexError:
                            pass    # upload tool will cause this since it doesn't have a job
        return self.history( trans )
        
    @web.expose
    def delete_async( self, trans, id = None, **kwd):
        if id:
            try:
                int( id )
            except:
                return "Dataset id '%s' is invalid" %str( id )
            history = trans.get_history()
            hda = self.app.model.HistoryDatasetAssociation.filter_by( dataset_id=id ).first()
            if hda:
                # Walk up parent datasets to find the containing history
                topmost_parent = hda
                while topmost_parent.parent:
                    topmost_parent = topmost_parent.parent
                assert topmost_parent in history.datasets, "Data does not belong to current history"
                # Mark deleted and cleanup
                hda.mark_deleted()
                hda.clear_associated_files()
                self.app.model.flush()
                trans.log_event( "Dataset id '%s' marked as deleted async" % str( id ) )
                if hda.parent_id is None:
                    try:
                        self.app.job_stop_queue.put( hda.creating_job_associations[0].job )
                    except IndexError:
                        pass    # upload tool will cause this since it doesn't have a job
        return "OK"

    ## ---- History management -----------------------------------------------

    @web.expose
    def history_options( self, trans ):
        """Displays a list of history related actions"""            
        return trans.fill_template( "/history/options.mako", user=trans.get_user(), history=trans.get_history() )

    @web.expose
    def history_delete( self, trans, id=None, **kwd):
        """Deletes a list of histories, ensures that histories are owned by current user"""
        history_names = []
        if id:
            if isinstance( id, list ):
                history_ids = id
            else:
                history_ids = [ id ]
            user = trans.get_user()
            for hid in history_ids:
                try:
                    int( hid )
                except:
                    return trans.show_message( "Invalid history: %s" % str( hid ) )
                history = self.app.model.History.get( hid )
                if history:
                    if history.user_id != None and user:
                        assert user.id == history.user_id, "History does not belong to current user"
                    history_names.append(history.name)
                    history.deleted = True
                    # If deleting the current history, make a new current.
                    if history == trans.get_history():
                        trans.new_history()
                else:
                    return trans.show_message( "Not able to find history %s" % str( hid ) )
                self.app.model.flush()
                trans.log_event( "History id %s marked as deleted" % str(hid) )
        else:
            return trans.show_message( "You must select at least one history to delete." )
        return trans.show_message( "History deleted: %s" % ",".join(history_names), refresh_frames=['history'] )

    @web.expose
    def clear_history( self, trans ):
        """Clears the history for a user"""
        history = trans.get_history()
        for hda in history.datasets:
            hda.deleted = True
            hda.dataset.deleted = True
            hda.clear_associated_files()
        self.app.model.flush()
        trans.log_event( "History id %s cleared" % (str(history.id)) )
        trans.response.send_redirect( url_for("/index" ) )

    @web.expose
    @web.require_login( "share histories with other users" )
    def history_share( self, trans, id=None, email="", **kwd ):
        send_to_err = ""
        if not id:
            id = trans.get_history().id
        if not isinstance( id, list ):
            id = [ id ]
        histories = []
        history_names = []
        for hid in id:
            histories.append( trans.app.model.History.get( hid ) )
            history_names.append(histories[-1].name) 
        if not email:
            return trans.fill_template("/history/share.mako", histories=histories, email=email, send_to_err=send_to_err)
        user = trans.get_user()  
        send_to_user = trans.app.model.User.get_by( email = email )
        if not send_to_user:
            send_to_err = "No such user"
        elif user.email == email:
            send_to_err = "You can't send histories to yourself"
        else:
            for history in histories:
                new_history = history.copy()
                new_history.name = history.name+" from "+user.email
                new_history.user_id = send_to_user.id
                trans.log_event( "History share, id: %s, name: '%s': to new id: %s" % (str(history.id), history.name, str(new_history.id)) )
            self.app.model.flush()
            return trans.show_message( "History (%s) has been shared with: %s" % (",".join(history_names),email) )
        return trans.fill_template( "/history/share.mako", histories=histories, email=email, send_to_err=send_to_err)

    @web.expose
    @web.require_login( "work with multiple histories" )
    def history_available( self, trans, id=None, as_xml=False, **kwd ):
        """
        List all available histories
        """
        if as_xml:
            trans.response.set_content_type('text/xml')
            return trans.fill_template( "/history/list_as_xml.mako" )
        if not isinstance( id, list ):
            id = [ id ]
        trans.log_event( "History id %s available" % str( id ) )
        return trans.fill_template( "/history/list.mako", ids=id, user=trans.get_user(), current_history=trans.get_history() )
        
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
            new_history = import_history.copy()
            new_history.name = "imported: "+new_history.name
            new_history.user_id = user.id
            galaxy_session = trans.get_galaxy_session()
            try:
                association = trans.app.model.GalaxySessionToHistoryAssociation.selectone_by( session_id=galaxy_session.id, history_id=new_history.id )
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
                association = trans.app.model.GalaxySessionToHistoryAssociation.selectone_by( session_id=galaxy_session.id, history_id=new_history.id )
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
    @web.require_login( "switch histories" )
    def history_switch( self, trans, id=None ):
        if not id:
            return trans.response.send_redirect( web.url_for( action='history_available' ) )
        else:
            new_history = trans.app.model.History.get( id )
            if new_history:
                galaxy_session = trans.get_galaxy_session()
                try:
                    association = trans.app.model.GalaxySessionToHistoryAssociation.selectone_by( session_id=galaxy_session.id, history_id=new_history.id )
                except:
                    association = None
                new_history.add_galaxy_session( galaxy_session, association=association )
                new_history.flush()
                trans.set_history( new_history )
                trans.log_event( "History switched to id: %s, name: '%s'" % (str(new_history.id), new_history.name ) )
                return trans.show_message( "History switched to: %s" % new_history.name,
                                           refresh_frames=['history'])
            else:
                return trans.show_error_message( "History not found" )
                
    @web.expose
    def history_new( self, trans ):
        trans.new_history()
        trans.log_event( "Created new History, id: %s." % str(trans.get_history().id) )
        return trans.show_message( "New history created", refresh_frames = ['history'] )

    @web.expose
    @web.require_login( "renames histories" )
    def history_rename( self, trans, id=None, name=None, **kwd ):
        user = trans.get_user()

        if not isinstance( id, list ):
            if id != None:
                id = [ id ]
        if not isinstance( name, list ):
            if name != None:
                name = [ name ]
        histories = []
        cur_names = []
        if not id:
            if not trans.get_history().user:
                return trans.show_error_message( "You must save your history before renaming it." )
            id = [trans.get_history().id]
        for history_id in id:
            history = trans.app.model.History.get( history_id )
            if history and history.user_id == user.id:
                histories.append(history)
                cur_names.append(history.name)
        if not name or len(histories)!=len(name):
            return trans.fill_template( "/history/rename.mako",histories=histories )
        change_msg = ""
        for i in range(len(histories)):
            if histories[i].user_id == user.id:
                if name[i] == histories[i].name:
                    change_msg = change_msg + "<p>History: "+cur_names[i]+" is already named: "+name[i]+"</p>"
                elif name[i] not in [None,'',' ']:
                    name[i] = escape(name[i])
                    histories[i].name = name[i]
                    histories[i].flush()
                    change_msg = change_msg + "<p>History: "+cur_names[i]+" renamed to: "+name[i]+"</p>"
                    trans.log_event( "History renamed: id: %s, renamed to: '%s'" % (str(histories[i].id), name[i] ) )
                else:
                    change_msg = change_msg + "<p>You must specify a valid name for History: "+cur_names[i]+"</p>"
            else:
                change_msg = change_msg + "<p>History: "+cur_names[i]+" does not appear to belong to you.</p>"
        return trans.show_message( "<p>%s" % change_msg, refresh_frames=['history'] ) 

    @web.expose
    def history_add_to( self, trans, history_id=None, file_data=None, name="Data Added to History",info=None,ext="txt",dbkey="?",**kwd ):
        """Adds a POSTed file to a History"""
        try:
            history = trans.app.model.History.get( history_id )
            hda = trans.app.model.HistoryDatasetAssociation( name=name, info=info, extension=ext, dbkey=dbkey, create_dataset=True )
            hda.flush()
            data_file = open( hda.file_name, "wb" )
            file_data.file.seek( 0 )
            data_file.write( file_data.file.read() )
            data_file.close()
            hda.dataset.state = hda.dataset.states.OK
            hda.init_meta()
            hda.set_meta()
            hda.flush()
            history.add_dataset( hda )
            history.flush()
            hda.set_peek()
            hda.set_size()
            hda.flush()
            trans.log_event( "Added dataset id '%s' to history id '%s'." % ( str( hda.dataset_id ),  str( history_id ) ) )
            return trans.show_ok_message( "Dataset id " + str( hda.dataset_id ) + " added to history id " + str( history_id ) + "." )
        except:
            return trans.show_error_message("Adding File to History has Failed")

    @web.expose
    def dataset_make_primary( self, trans, id=None):
        """Copies a dataset and makes primary"""
        try:
            old_hda = self.app.model.HistoryDatasetAssociation.filter_by( dataset_id=id ).first()
            new_hda = old_hda.copy()
            history = trans.get_history()
            history.add_dataset( new_hda )
            new_hda.flush()
            return trans.show_message( "<p>Secondary dataset has been made primary.</p>", refresh_frames=['history'] ) 
        except:
            return trans.show_error_message( "<p>Failed to make secondary dataset primary.</p>" ) 

    @web.expose
    def masthead( self, trans ):
        brand = trans.app.config.get( "brand", "" )
        if brand:
            brand ="<span class='brand'>/%s</span>" % brand
        wiki_url = trans.app.config.get( "wiki_url", "http://g2.trac.bx.psu.edu/" )
        bugs_email = trans.app.config.get( "bugs_email", "mailto:galaxy-bugs@bx.psu.edu"  )
        blog_url = trans.app.config.get( "blog_url", "http://g2.trac.bx.psu.edu/blog"   )
        screencasts_url = trans.app.config.get( "screencasts_url", "http://g2.trac.bx.psu.edu/wiki/ScreenCasts" )
        return trans.fill_template( "/root/masthead.mako", brand=brand, wiki_url=wiki_url, 
          blog_url=blog_url,bugs_email=bugs_email, screencasts_url=screencasts_url )

    @web.expose
    def dataset_errors( self, trans, id=None, **kwd ):
        """View/fix errors associated with dataset"""
        hda = trans.app.model.HistoryDatasetAssociation.filter_by( dataset_id=id ).first()
        p = kwd
        if p.get("fix_errors", None):
            # launch tool to create new, (hopefully) error free dataset
            tool_params = {}
            tool_params["tool_id"] = 'fix_errors'
            tool_params["runtool_btn"] = 'T'
            tool_params["input"] = id
            tool_params["ext"] = hda.ext
            # send methods selected
            repair_methods = hda.datatype.repair_methods( hda )
            methods = []
            for method, description in repair_methods:
                if method in p:
                    methods.append( method )
            tool_params["methods"] = ",".join(methods)
            url = "/tool_runner/index?" + urllib.urlencode(tool_params)
            trans.response.send_redirect(url)                
        else:
            history = trans.app.model.History.get( hda.history_id )
            return trans.fill_template('dataset/validation.tmpl', data=hda, history=history)

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
