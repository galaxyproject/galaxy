import bz2, gzip

def open_compressed( filename, mode='r' ):
    if filename.endswith( ".bz2" ):
        return bz2.BZ2File( filename, mode )
    elif filename.endswith( ".gz" ):
        return gzip.GzipFile( filename, mode )
    else:
        return file( filename, mode )
