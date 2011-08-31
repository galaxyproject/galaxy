"""
Provides utilities for working with image files.
"""
import logging, imghdr

try:
    import Image as PIL
except ImportError:
    try:
        from PIL import Image as PIL
    except:
        PIL = None

log = logging.getLogger(__name__)

def image_type( filename, image=None ):
    format = ''
    if PIL is not None:
        if image is not None:
            format = image.format
        else:
            try:
                im = PIL.open( filename )
                format = im.format
                im.close()
            except:
                return False
    else:
        format = imghdr.what( filename )
        if format is not None:
            format = format.upper()
        else:
            return False
    return format
def check_image_type( filename, types, image=None ):
    format = image_type( filename, image )
    # First check if we can  use PIL        
    if format in types:
        return True
    return False
def get_image_ext ( file_path, image ):
    #determine ext
    format = image_type( file_path, image )    
    if format in [ 'JPG','JPEG' ]:
        return 'jpg'
    if format == 'PNG':
        return 'png'
    if format == 'TIFF':
        return 'tiff'
    if format == 'BMP':
        return 'bmp'
    if format == 'GIF':
        return 'gif'
    if format == 'IM':
        return 'im'
    if format == 'PCD':
        return 'pcd'
    if format == 'PCX':
        return 'pcx'
    if format == 'PPM':
        return 'ppm'
    if format == 'PSD':
        return 'psd'
    if format == 'XBM':
        return 'xbm'
    if format == 'XPM':
        return 'xpm'
    if format == 'RGB':
        return 'rgb'
    if format == 'PBM':
        return 'pbm'
    if format == 'PGM':
        return 'pgm'
    if format == 'EPS':
        return 'eps'
    return None
