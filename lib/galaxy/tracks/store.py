import os
import re
from string import Template
from galaxy.util import sanitize_text

# extra mappings/escape to keep users from traversing around the
# filesystem and wreaking havoc
extra_mappings = { r"/": "__fs__", r"^manifest.tab$": "__manifest.tab__" }

def sanitize_name( name ):
    name = sanitize_text( name )
    for key, value in extra_mappings.items():
        name = re.sub( key, value, name )
    return name

class TemplateSubber( object ):
    def __init__(self, obj):
        self.obj = obj
    def get( self, key, default=None ):
        return getattr(self.obj, key, default)
    def __getitem__(self, key):
        return self.get(key)

class TrackStoreManager( object ):
    def __init__(self, path=""):
        self.path = path

    def get( self, dataset ):
        s = Template(self.path)
        return TrackStore( path=s.substitute(TemplateSubber(dataset)) )

class TrackStore( object ):
    MANIFEST_NAME = "manifest.tab"

    def __init__(self, path=""):
        self.path = path

    def get_manifest( self ):
        if not self.exists: raise self.DoesNotExist("TrackStore at %s does not exist." % self.path)
        manifest_path = os.path.join( self.path, self.MANIFEST_NAME )
        if os.path.exists( manifest_path ):
            manifest = {}
            for line in open( manifest_path ):
                line = line.rstrip("\n\r")
                fields = line.split("\t")
                manifest[fields[0]] = fields[1:]
            return manifest
        else:
            raise self.DoesNotExist( "Manifest for TrackStore object could not be found." )

    def get(self, chrom="chr1", resolution=None, **kwargs):
        if not self.exists: raise self.DoesNotExist("TrackStore at %s does not exist." % self.path)
        object_path = self._get_object_path( chrom, resolution )
        if os.path.exists( object_path ):
            return open( object_path, "rb" )
        else:
            try:
                return kwargs['default']
            except KeyError:
                raise self.DoesNotExist("TrackStore object at %s does not exist." % object_path )

    def set(self, chrom="chr1", resolution=None, data=None):
        if not self.exists: self._build_path( self.path )
        if not data: return
        object_path = self._get_object_path( chrom, resolution )
        fd = open( object_path, "wb" )
        fd.write( data )
        fd.close()
        
    def _get_object_path( self, chrom, resolution ):
        object_name = sanitize_name(chrom)
        if resolution: object_name += "_%d" % resolution
        return os.path.join( self.path, object_name )

    def _build_path( self, path ):
        try:
            os.mkdir( path )
        except OSError:
            self._build_path( os.path.dirname( path ) )
            os.mkdir( path )

    @property
    def exists(self):
        return os.path.exists( self.path )

    class DoesNotExist( Exception ):
        pass
