"""
Contains data definitions
"""
import logging
import data, interval, images, sequence
from cookbook.patterns import Bunch

log = logging.getLogger(__name__)

datatypes_by_extension = { 
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
    'gmaj.zip' : images.Gmaj(),
    'laj'      : images.Laj(),
    'lav'      : sequence.Lav(),
    'html'     : images.Html(),
    'customtrack' : interval.CustomTrack()
}

def get_datatype_by_extension( ext ):
    """
    Returns a datatype based on an extension
    """
    try:
        builder = datatypes_by_extension[ext]
    except KeyError:
        builder = data.Text()
        log.warning('unkown extension in data factory %s' % ext)
    return builder 

def change_datatype( data, ext ):
    data.extension = ext
    data.init_meta()
    if data.has_data():
        data.set_peek()
    return data

def old_change_datatype(data, ext):
    """
    Creates and returns a new datatype based on an existing data and an extension
    """
    newdata = factory(ext)(id=data.id)
    for key, value in data.__dict__.items():
        setattr(newdata, key, value)
    newdata.ext = ext
    return newdata
