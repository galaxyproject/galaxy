import os, shutil, urllib, StringIO, re
from galaxy import datatypes, jobs
from galaxy.datatypes import sniff
from galaxy import model, util

import sys, traceback
        
class UploadToolAction( object ):
    """
    Action for uploading files
    """
    empty = False
    
    def execute( self, tool, trans, incoming={} ):
        data_file = incoming['file_data']
        file_type = incoming['file_type']
        dbkey = incoming['dbkey']
        url_paste = incoming['url_paste']
        space_to_tab = False 
        if 'space_to_tab' in incoming:
            if incoming['space_to_tab']  not in ["None", None]:
                space_to_tab = True
        info = "uploaded file"
        temp_name = ""
        data_list = []
        self.empty = False
        if 'filename' in dir(data_file):
            try:
                file_name = data_file.filename
                file_name = file_name.split('\\')[-1]
                file_name = file_name.split('/')[-1]
                data_list.append( self.add_file(trans, data_file.file, file_name, file_type, dbkey, "uploaded file",space_to_tab=space_to_tab) )
            except BadFileException:
                return self.upload_empty( trans, "Error", "error in uploaded file")
            except:
                pass
        
        if url_paste not in [None, ""]:
            if url_paste[0:7].lower() == "http://" or url_paste[0:6].lower() == "ftp://" :
                url_paste = url_paste.replace("\r","").split("\n")
                for line in url_paste:
                    try:
                        data_list.append( self.add_file(trans, urllib.urlopen(line), line, file_type, dbkey, "uploaded url",space_to_tab=space_to_tab) )
                    except BadFileException:
                        return self.upload_empty( trans, "Error", "error in uploaded file")
                    except:
                        pass
            else:
                try:
                    data_list.append( self.add_file(trans, StringIO.StringIO(url_paste), 'Pasted Entry', file_type, dbkey, "pasted entry",space_to_tab=space_to_tab) )
                except BadFileException:
                    return self.upload_empty( trans, "Error", "error in uploaded file" )
                except:
                    pass
        if self.empty:
            return self.upload_empty(trans, "Empty file error:", "you attempted to upload an empty file")
        elif len(data_list)<1:
            return self.upload_empty(trans, "No data error:","either you pasted no data, the url you specified is invalid, or you have not specified a file")
        return dict( output=data_list[0] )

    def upload_empty(self, trans, err_code, err_msg):
        data = trans.app.model.Dataset()
        data.name = err_code 
        data.extension = "text"
        data.dbkey = "?"
        data.info = err_msg
        data.flush()
        data.state = data.states.EMPTY
        trans.history.add_dataset( data )
        trans.app.model.flush()
        return dict( output=data )

    def add_file(self, trans, file_obj, file_name, file_type, dbkey, info, space_to_tab = False ):
        temp_name = sniff.stream_to_file(file_obj)

        # Check against html:
        if self.check_html( temp_name ):
            self.empty = True
            raise BadFileException( "Error in uploaded file" )
        
        sniff.convert_newlines(temp_name)
        
        if space_to_tab:
            sniff.sep2tabs(temp_name)
        
        if file_type == 'auto':
            ext = sniff.guess_ext(temp_name)    
        else:
            ext = file_type

        data = trans.app.model.Dataset()
        data.name = file_name
        data.extension = ext
        data.dbkey = dbkey
        data.info = info
        data.flush()
        shutil.move(temp_name, data.file_name)
        data.state = data.states.OK
        data.init_meta()
        data.set_peek()
        """
        gvk: 07/16/07: I believe this will soon be going away.  Tests are breaking, so I'll comment it out for now...
        if isinstance( data.datatype, datatypes.interval.Interval ):
            if data.missing_meta():
                if isinstance( data.datatype, datatypes.interval.Bed ):
                    data.extension = 'interval'
                if data.missing_meta():
                    data.extension = 'tabular'
        """

        # validate incomming data
        """
        Commented by greg on 3/14/07
        for error in data.datatype.validate( data ):
            data.add_validation_error( 
                model.ValidationError( message=str( error ), err_type=error.__class__.__name__, attributes=util.object_to_string( error.__dict__ ) ) )
        """
        if data.has_data():
            trans.history.add_dataset( data, genome_build=dbkey )
            trans.app.model.flush()
            trans.log_event("Added dataset %d to history %d" %(data.id, trans.history.id), tool_id="upload")
        else:
            self.empty = True
        return data

    def check_html( self, temp_name ):
        temp = open(temp_name, "U")
        regexp = re.compile( "<([A-Z][A-Z0-9]*)[^>]*>", re.I )
        lineno = 0
        for line in temp:
            lineno += 1
            matches = regexp.search( line )
            if matches:
                temp.close()
                return True
            if lineno > 1000:
                break
        temp.close()
        return False

class BadFileException( Exception ):
    pass
