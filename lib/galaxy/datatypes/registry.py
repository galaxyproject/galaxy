"""
Provides mapping between extensions and datatypes, mime-types, etc.
"""
import logging
import data, interval, images, sequence

class Registry( object ):
    def __init__( self, datatypes = [] ):
        self.log = logging.getLogger(__name__)
        self.datatypes_by_extension = {}
        self.mimetypes_by_extension = {}
        for ext, kind in datatypes:
            try:
                mime_type = None
                fields = kind.split(",")
                if len(fields)>1:
                    kind = fields[0].strip()
                    mime_type = fields[1].strip()
                fields = kind.split(":")
                datatype_module = fields[0]
                datatype_class = fields[1]
                fields = datatype_module.split(".")
                module = __import__(fields.pop(0))
                for mod in fields: module = getattr(module,mod)
                self.datatypes_by_extension[ext] = getattr(module, datatype_class)()
                if mime_type is None:
                    # Use default mime type as per datatype spec
                    mime_type = self.datatypes_by_extension[ext].get_mime()
                self.mimetypes_by_extension[ext] = mime_type
            except:
                self.log.warning('error loading datatype: %s' % ext)
        #default values
        if len(self.datatypes_by_extension) < 1:
            self.datatypes_by_extension = { 
                'data'     : data.Data(), 
                'bed'      : interval.Bed(), 
                'txt'      : data.Text(), 
                'text'     : data.Text(),
                'interval' : interval.Interval(), 
                'tabular'  : interval.Tabular(),
                'png'      : images.Image(), 
                'pdf'      : images.Image(), 
                'fasta'    : sequence.Fasta(),
                'maf'      : sequence.Maf(),
                'axt'      : sequence.Axt(),
                'gff'      : interval.Gff(),
                'wig'      : interval.Wiggle(),
                'gmaj.zip' : images.Gmaj(),
                'laj'      : images.Laj(),
                'lav'      : sequence.Lav(),
                'html'     : images.Html(),
                'customtrack' : interval.CustomTrack(),
                'gbrowsetrack' : interval.GBrowseTrack()
            }
            self.mimetypes_by_extension = { 
                'data'     : 'application/octet-stream', 
                'bed'      : 'text/plain', 
                'txt'      : 'text/plain', 
                'text'     : 'text/plain',
                'interval' : 'text/plain', 
                'tabular'  : 'text/plain',
                'png'      : 'image/png', 
                'pdf'      : 'application/pdf', 
                'fasta'    : 'text/plain',
                'maf'      : 'text/plain',
                'axt'      : 'text/plain',
                'gff'      : 'text/plain',
                'wig'      : 'text/plain',
                'gmaj.zip' : 'application/zip',
                'laj'      : 'text/plain',
                'lav'      : 'text/plain',
                'html'     : 'text/html',
                'customtrack' : 'text/plain',
                'gbrowsetrack' : 'text/plain'
            }
    
    def get_mimetype_by_extension(self, ext ):
        """
        Returns a mimetype based on an extension
        """
        try:
            mimetype = self.mimetypes_by_extension[ext]
        except KeyError:
            #datatype was never declared
            mimetype = 'application/octet-stream'
            self.log.warning('unkown mimetype in data factory %s' % ext)
        return mimetype
    
    def get_datatype_by_extension(self, ext ):
        """
        Returns a datatype based on an extension
        """
        try:
            builder = self.datatypes_by_extension[ext]
        except KeyError:
            builder = data.Text()
            self.log.warning('unknown extension in data factory %s' % ext)
        return builder 

    def change_datatype(self, data, ext ):
        data.extension = ext
        # call init_meta and copy metadata from itself.  The datatype
        # being converted *to* will handle any metadata copying and
        # initialization.
        data.init_meta( copy_from=data )
        if data.has_data():
            data.set_peek()
        return data

    def old_change_datatype(self, data, ext):
        """
        Creates and returns a new datatype based on an existing data and an extension
        """
        newdata = factory(ext)(id=data.id)
        for key, value in data.__dict__.items():
            setattr(newdata, key, value)
        newdata.ext = ext
        return newdata
