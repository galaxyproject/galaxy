"""Provides utilities for working with image files."""
import imghdr
import logging

try:
    import Image as PIL
except ImportError:
    try:
        from PIL import Image as PIL
    except:
        PIL = None

log = logging.getLogger(__name__)


def image_type( filename ):
    fmt = None
    if PIL is not None:
        try:
            im = PIL.open( filename )
            fmt = im.format
            im.close()
        except:
            # We continue to try with imghdr, so this is a rare case of an
            # exception we expect to happen frequently, so we're not logging
            pass
    if not fmt:
        fmt = imghdr.what( filename )
    if fmt:
        return fmt.upper()
    else:
        return False


def check_image_type( filename, types ):
    fmt = image_type( filename )
    if fmt in types:
        return True
    return False


def get_image_ext( file_path ):
    # determine ext
    fmt = image_type( file_path )
    if fmt in [ 'JPG', 'JPEG' ]:
        return 'jpg'
    if fmt == 'PNG':
        return 'png'
    if fmt == 'TIFF':
        return 'tiff'
    if fmt == 'BMP':
        return 'bmp'
    if fmt == 'GIF':
        return 'gif'
    if fmt == 'IM':
        return 'im'
    if fmt == 'PCD':
        return 'pcd'
    if fmt == 'PCX':
        return 'pcx'
    if fmt == 'PPM':
        return 'ppm'
    if fmt == 'PSD':
        return 'psd'
    if fmt == 'XBM':
        return 'xbm'
    if fmt == 'XPM':
        return 'xpm'
    if fmt == 'RGB':
        return 'rgb'
    if fmt == 'PBM':
        return 'pbm'
    if fmt == 'PGM':
        return 'pgm'
    return None
