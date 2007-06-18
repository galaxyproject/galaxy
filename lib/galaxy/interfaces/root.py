"""
Contains the main interface in the Universe class
"""
import logging, os, sets, string, shutil
import re, socket

from galaxy import util, datatypes, jobs, web, util
import common
from cgi import escape, FieldStorage
import urllib

log = logging.getLogger( __name__ )

class Universe(common.Root):
    pref_cookie_name = 'universe_prefs'
    
    @web.expose
    def generate_error( self, trans ):
        raise Exception( "Fake error!" )
    
    @web.expose
    def default(self, trans, target1=None, target2=None, **kwd):
        return 'This link may not be followed from within Galaxy.'
    
    @web.expose
    def index(self, trans, id=None, tool_id=None, mode=None, **kwd):
        if mode:
            trans.set_cookie(name=self.pref_cookie_name, value=mode)
        else:
            mode = trans.get_cookie(name=self.pref_cookie_name)
        trans.ensure_valid_galaxy_session()
        result = trans.fill_template('index_frames.tmpl', mode=mode)
        return [ result ]

    @web.expose
    def tool_menu( self, trans ):
        return trans.fill_template('tool_menu.tmpl', toolbox=self.get_toolbox() )

    @web.expose
    def last_hid( self, trans ):
        """Returns the largest (last) history id"""
        trans.response.set_content_type("text/plain")
        history = trans.get_history()
        # if history.datasets :
        #     maxhid = max( [ data.hid for data in history.datasets ] )
        # else:
        #     maxhid = -1
        if len( history.datasets ) > 0:
            return len( history.datasets ) + 1
        else:
            return -1
        return str(maxhid)
        
    @web.expose
    def last_dataset_id( self, trans ):
        """Returns the largest (last) dataset id"""
        trans.response.set_content_type("text/plain")
        history = trans.get_history()
        # if history.datasets :
        #     maxhid = max( [ data.hid for data in history.datasets ] )
        # else:
        #     maxhid = -1
        if len( history.datasets ) > 0:
            return history.datasets[-1].id
        else:
            return -1

    @web.expose
    def history( self, trans, id=None, template='history.tmpl' ):
        # history = trans.get_history(id=id)
        try:
            history = trans.get_history()
        except:
            return self.history_new(trans)
        if template.endswith('.xml'):
            trans.response.set_content_type('text/xml')        
        mode = trans.get_cookie(name=self.pref_cookie_name)
        return trans.fill_template(template, history=history, mode=mode )

    @web.expose
    def display(self, trans, id=None, hid=None, tofile=None, toext=".txt"):
        """
        Returns data directly into the browser. 
        Sets the mime-type according to the extension
        """
        
        if hid is not None:
            history = trans.get_history()
            hid = int( hid )
            for dataset in history.datasets:
                if dataset.hid == hid:
                    data = dataset
                    break
            else:
                raise Exception( "No dataset with hid '%d'" % hid )
        else:
            data = self.app.model.Dataset.get( id )
            
        if data:
            mime = trans.app.datatypes_registry.get_mimetype_by_extension( data.extension.lower() )
            trans.response.set_content_type(mime)
            if tofile:
                fStat = os.stat(data.file_name)
                trans.response.headers['Content-Length'] = int(fStat.st_size)
                if toext[0:1] != ".":
                    toext = "." + toext
                trans.response.headers["Content-Disposition"] = "attachment; filename=GalaxyHistoryItem-%s%s" % (data.hid, toext)
            trans.log_event( "Display dataset id: %s" % str(id) )
            try:
                return open( data.file_name )
            except: 
                return "This item contains no content"
        else:
            return "No data with id=%s" % id
        
    @web.expose
    def display_bed( self, trans, id=None ):
        """Returns a bed file"""
        data = self.app.model.Dataset.get( id )
        if data:
            if isinstance(data.datatype, datatypes.interval.Interval) or isinstance(data.datatype, datatypes.interval.CustomTrack):
                mime = trans.app.datatypes_registry.get_mimetype_by_extension( data.extension.lower() )
                trans.response.set_content_type(mime)
                file_name = data.as_bedfile()
                trans.log_event( "Display dataset id %s as BED" % str(id) )
                return open(file_name)
            else:
                return 'This file cannot be displayed as bed'
        else:
            return "No data with id=%s" % id

    @web.expose
    def peek(self, trans, id=None):
        """Returns a 'peek' at the data"""
        data = self.app.model.Dataset.get( id )
        if data:
            yield "<html><body><pre>"
            yield data.peek
            yield "</pre></body></html>"
        else:
            yield "No data with is=%s" % id

    @web.expose
    def edit(self, trans, id=None, hid=None, **kwd):
        """Returns data directly into the browser. Sets the mime-type according to the extension"""
        if hid is not None:
            history = trans.get_history()
            # TODO: hid handling
            data = history.datasets[ int( hid ) - 1 ]
        else:
            data = self.app.model.Dataset.get( id )

        if data is None:
            self.err_msg = 'No such data exists!' # a user should never get this!
            return self.index( trans )

        p = util.Params(kwd, safe=False)
        if p.edit_genome_btn:
            err = None
            # check for "valid" column assignments first
            # Patch: don't validate these fields for mafs, etc.
            # This will all go away soon
            if isinstance( data.datatype, datatypes.interval.Tabular ):
                for attr in 'chromCol', 'startCol', 'endCol', 'strandCol':
                    try:
                        num = int( getattr(p, attr) )
                        if num < 0: raise Exception()
                    except:
                        if getattr(p, attr) != "" or attr != 'strandCol':
                            err = "Column assignments must be numbers greater than zero.  Strand column may be ommitted (set to 0)."
                if err:
                    trans.log_event( "Edit submitted bad values on dataset %s" % str(id) )
                    return trans.fill_template( "edit.tmpl", data=data, dbnames=util.dbnames, err=err )
            
            data.name  = p.name
            data.info  = p.info
            data.dbkey = p.dbkey
            
            # detect metadata changes, kind of ugly
            changed = False
            for attr in 'chromCol', 'startCol', 'endCol', 'strandCol':
                try:
                    oldv = str(getattr(data.metadata, attr)).strip() or None
                except:
                    oldv = None
                newv = str(getattr(p, attr)).strip() or None
                if oldv != newv:
                    changed = True
            
            if changed and isinstance( data.datatype, datatypes.interval.Tabular ):
                data.metadata.chromCol  = p.chromCol
                data.metadata.startCol  = p.startCol
                data.metadata.endCol    = p.endCol
                data.metadata.strandCol = p.strandCol or '0'
                data.mark_metadata_changed()
                if data.missing_meta():
                    data.extension = 'tabular'
                else:
                    data.extension = 'interval'
                    
            data.flush()
            trans.log_event( "Completed editing of dataset id %s" % str(id) )
            return trans.fill_template( "edit_complete.tmpl" )
        else:
            trans.log_event( "Opened edit view on dataset %s" % str(id) )
            return trans.fill_template( "edit.tmpl", data=data, dbnames=util.dbnames, err=None )

    @web.expose
    def delete( self, trans, id = None, **kwd):
        if id:
            if isinstance( id, list ):
                dataset_ids = id
            else:
                dataset_ids = [ id ]
            history = trans.get_history()
            for id in dataset_ids:
               data = self.app.model.Dataset.get( id )
               if data:
                   assert data in history.datasets, "Data does not belong to current history"
                   # assert data.parent == None, "You must delete the primary dataset first."
                   # history.datasets.remove( data )
                   data.deleted = True
                   trans.log_event( "Dataset id %s marked as deleted" % str(id) )
            self.app.model.flush()
        return self.history( trans )
        
    @web.expose
    def delete_async( self, trans, id = None, **kwd):
        if id:
            history = trans.get_history()
            data = self.app.model.Dataset.get( id )
            if data:
               assert data in history.datasets, "Data does not belong to current history"
               # assert data.parent == None, "You must delete the primary dataset first."
               # history.datasets.remove( data )
               data.deleted = True
               trans.log_event( "Dataset id %s marked as deleted async" % str(id) )
            self.app.model.flush()
        return "OK"

    @web.expose
    def history_delete( self, trans, id = None, **kwd):
        """Deletes a list of histories, ensures that histories are owned by current user"""
        history_names = []
        if id:
            if isinstance( id, list ):
                history_ids = id
            else:
                history_ids = [ id ]
            user = trans.get_user()
            for hid in history_ids:
                history = self.app.model.History.get( hid )
                if history:
                    if history.user_id != None and user:
                        assert user.id == history.user_id, "History does not belong to current user"
                    history_names.append(history.name)
                    history.deleted = True
                    # If deleting the current history, make a new current.
                    if history == trans.get_history():
                        trans.new_history()
                trans.log_event( "History id %s marked as deleted" % str(hid) )
                self.app.model.flush()
            
        else:
            return trans.show_message( "You must select at least one history to delete." )
        return trans.show_message( "History deleted: %s" % ",".join(history_names),
                                           refresh_frames=['history'])

    @web.expose
    def clear_history( self, trans ):
        """Clears the history for a user"""
        history = trans.get_history()
        for dataset in history.datasets:
            dataset.deleted = True
        self.app.model.flush()
        trans.log_event( "History id %s cleared" % (str(history.id)) )
        trans.response.send_redirect("/index")

    @web.expose
    def tool_help( self, trans, id ):
        """Return help page for tool identified by 'id' if available"""
        toolbox = self.get_toolbox()
        tool = toolbox.tools_by_id.get(id, '')
        yield "<html><body>"
        if not tool:
            yield "Unkown tool id '%s'" % id
        elif tool.help:
            yield tool.help
        else:
            yield "No additional help available for tool '%s'" % tool.name
        yield "</body></html>"

    # @web.expose
    # def share_history( self, trans, id=None, create=None ):
    #     """Shares the history"""
    #     history = trans.get_history()
    #     if create:
    #         # create a new history
    #         history = obj.History()
    #         history.store()
    #         history = trans.get_history(id=history.id)
    #         trans.response.send_redirect("/index")
    #     elif id:
    #         # load a previous one
    #         history = trans.get_history(id=id)
    #         trans.response.send_redirect("/index") 
    #     
    #     url = '%s/share_history?id=%s' % (trans.request.base, history.id)
    #     return trans.fill_template( "share.tmpl", url=url)


    @web.expose
    def history_share( self, trans, id=None, email=None, **kwd ):
        send_to_err = ""
        user = trans.get_user()
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
            return trans.fill_template("history_share.tmpl", histories=histories, user=user, email=email, send_to_err=send_to_err)
            
        send_to_user = trans.app.model.User.get_by( email = email )
        if not send_to_user:
            send_to_err = "No such user"
        elif user.email == email:
            send_to_err = "You can't send histories to yourself"
        else:
            for history in histories:
                new_history = self.copy_history(history, trans)
                new_history.name = history.name+" from "+user.email
                new_history.user_id = send_to_user.id
                """
                gvk TODO: how should we handle galaxy_session_to_history association here?
                I'll do the following for now, but not sure if this is what we want...
                """
                new_history.add_galaxy_session(trans.get_galaxy_session( create=True ))
                trans.log_event( "History share, id: %s, name: '%s': to new id: %s" % (str(history.id), history.name, str(new_history.id)) )
            self.app.model.flush()
            return trans.show_message( "History (%s) has been shared with: %s" % (",".join(history_names),email) )
        return trans.fill_template("history_share.tmpl", histories=histories, user=user, email=email, send_to_err=send_to_err)

    @web.expose
    def history_available( self, trans, id=None, **kwd ):
        if not isinstance( id, list ):
            id = [ id ]
        trans.log_event( "History id %s available" % str( id ) )
        return trans.fill_template( "history_available.tmpl", ids=id )
        
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
            new_history = self.copy_history(import_history, trans)
            new_history.name = "imported: "+new_history.name
            new_history.user_id = user.id
            new_history.add_galaxy_session(trans.get_galaxy_session( create=True ))
            new_history.flush()
            if not user_history.datasets:
                trans.set_history( new_history )
            trans.log_event( "History imported, id: %s, name: '%s': " % (str(new_history.id) , new_history.name ) )
            return trans.fill_template("history_imported.tmpl", history=new_history)
        elif not user_history.datasets or confirm:
            new_history = self.copy_history(import_history, trans)
            new_history.name = "imported: "+new_history.name
            new_history.user_id = None
            new_history.add_galaxy_session(trans.get_galaxy_session( create=True ))
            new_history.flush()
            trans.set_history( new_history )
            trans.log_event( "History imported, id: %s, name: '%s': " % (str(new_history.id) , new_history.name ) )
            return trans.fill_template("history_imported.tmpl", history=new_history)
        return trans.fill_template("history_import.tmpl", history=import_history)

    @web.expose
    def history_switch( self, trans, id=None ):
        if not id:
            return trans.fill_template( "history_switch.tmpl" )
        else:
            new_history = trans.app.model.History.get( id )
            if new_history:
                new_history.add_galaxy_session(trans.get_galaxy_session( create=True ))
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
        return self.history( trans )
        
    @web.expose
    def history_store( self, trans, name=None ):
        user = trans.get_user()
        if not user:
            return trans.show_error_message( "Must be logged in to save history" )
        history = trans.get_history()
        if history.user:
            if history.user == user:
                return trans.show_error_message( "Current history already stored (name: %s)" % history.name )
            else:
                return trans.show_error_message( "Current history already associated with a different user" )
        if not name:
            return trans.fill_template( "history_store.tmpl" )
        name = escape(name.replace("\n","").replace("\r",""))
        history.name = name
        history.user = user
        trans.app.model.flush()
        trans.log_event( "History stored, id: %s, name: '%s'" % (str(history.id), history.name ) )
        return trans.show_message( "Current history stored as %s" % name, refresh_frames=['history']  )        

    @web.expose
    def history_rename( self, trans, id=None, name=None, **kwd ):
        user = trans.get_user()
        if not user:
            return trans.show_error_message( "Must be logged in to rename your history" )
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
            return trans.fill_template( "history_rename.tmpl",histories=histories )
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
        return trans.show_message( "<p><h2>Rename history</h2>%s" % change_msg, refresh_frames=['history'] ) 

    @web.expose
    def history_add_to( self, trans, history_id=None, file_data=None, name="Data Added to History",info=None,ext="text",dbkey="?",**kwd ):
        """Adds a POSTed file to a History"""
        try:
            history = trans.app.model.History.get( history_id )
            data = trans.app.model.Dataset()
            data.name = name
            data.extension = ext
            data.dbkey = dbkey
            data.info = info
            data.flush()
            data_file = open(data.file_name, "w")
            file_data.file.seek(0)
            data_file.writelines(file_data.file.readlines())
            data_file.close()
            data.state = data.states.OK
            data.init_meta()
            data.flush()
            history.add_dataset( data)
            history.flush()
            data.set_peek()
            data.flush()
            trans.log_event("Added dataset %d to history %d" %(data.id, trans.history.id))
            return trans.show_ok_message("Dataset "+str(data.hid)+" added to history "+str(history_id)+".")
        except:
            return trans.show_error_message("Adding File to History has Failed")

    @web.expose
    def dataset_make_primary( self, trans, id=None):
        """Copies a dataset and makes primary"""
        try:
            old_data = self.app.model.Dataset.get( id )
            new_data = self.copy_dataset(old_data, trans)
            ## new_data.parent = None
            ## history = trans.app.model.History.get( old_data.history_id )
            history = trans.get_history()
            history.add_dataset(new_data)
            new_data.flush()
            return trans.show_message( "<p>Secondary dataset has been made primary.</p>", refresh_frames=['history'] ) 
        except:
            return trans.show_error_message( "<p>Failed to make secondary dataset primary.</p>" ) 

    @web.expose
    def masthead( self, trans ):
        return trans.fill_template( "masthead.tmpl" )

    @web.expose
    def dataset_errors( self, trans, id=None, **kwd ):
        """View/fix errors associated with dataset"""
        data = trans.app.model.Dataset.get( id )
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

    # ---- Work methods -----------------------------------------------------
    
    def copy_dataset(self, src, trans, parent_id=None):
        des = self.app.model.Dataset()
        des.flush()
        des.change_datatype( src.ext )
        des.name = src.name
        des.info = src.info
        des.blurb = src.blurb
        des.peek = src.peek
        des.extension = src.extension
        des.dbkey = src.dbkey
        des.state = src.state
        des.metadata = src.metadata
        des.hid = src.hid
        ## des.parent_id = parent_id
        shutil.copyfile(src.file_name,des.file_name)
        des.hid = src.hid
        des.designation = src.designation
        des.flush()
        return des
        
    def copy_history(self, src, trans):
        des = self.app.model.History()
        des.flush()
        des.name = src.name
        des.user_id = src.user_id
        for data in src.datasets:
            new_data = self.copy_dataset(data, trans)
            des.add_dataset(new_data)
            new_data.hid = data.hid
            new_data.flush()
            for child_assoc in data.children:
                new_child = self.copy_dataset(child_assoc.child, trans)
                new_assoc = self.app.model.DatasetAssociation( child.designation )
                new_assoc.child = new_child
                new_assoc.parent = new_data
                #des.add_dataset(new_child, parent_id = new_data.id)
                new_child.flush()
        des.hid_counter = src.hid_counter
        self.app.model.flush()
        return des
