import json
import logging

from galaxy.datatypes.data import get_file_peek, Text
from galaxy.datatypes.text import Json
from galaxy.datatypes.sniff import build_sniff_from_prefix
from galaxy.util import nice_size

log = logging.getLogger(__name__)


###########################
## AMP extended Json Types
###########################

@build_sniff_from_prefix
class AmpJson(Json):
    label = "AMP JSON"

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek(dataset.file_name)
            dataset.blurb = self.label
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disc'

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return self.label + " file (%s)" % (nice_size(dataset.get_size()))

# Deprecated, use Segment instead
@build_sniff_from_prefix
class Segments(AmpJson):
    file_ext = "segments"
    label = "AMP Segments JSON (depreated, use segnment instead)"

    def sniff_prefix(self, file_prefix):
        # this sniffer should not be called and it's not included as one of the sniffers in datatypes config;
        # just in case it's called, it always returns false so no new dataset will be associated with this type 
        return false
       
@build_sniff_from_prefix
class Segment(AmpJson):
    file_ext = "segment"
    label = "AMP Segment JSON"

    def _looks_like_json(self, file_prefix):
        # Pattern used by SequenceSplitLocations
        if file_prefix.file_size < 50000 and not file_prefix.truncated:
            # If the file is small enough - don't guess just check.
            try:
                # exclude simple types, must set format in these cases
                item = json.loads(file_prefix.contents_header)
                assert isinstance(item, (list, dict))
                if 'segments' in item and 'media' in item:
                    return True
            except Exception:
                return False
        else:
            start = file_prefix.string_io().read(100).strip()
            if start:
                return "\"media\":" in start and "\"segments\":" in start
            return False
       
@build_sniff_from_prefix
class Transcript(AmpJson):
    file_ext = "transcript"
    label = "AMP Transcript JSON"

    def _looks_like_json(self, file_prefix):
        # Pattern used by SequenceSplitLocations
        if file_prefix.file_size < 50000 and not file_prefix.truncated:
            # If the file is small enough - don't guess just check.
            try:
                # exclude simple types, must set format in these cases
                item = json.loads(file_prefix.contents_header)
                assert isinstance(item, (list, dict))
                if not ('results' in item and 'media' in item):
                    return False                
                results = item['results']
                if 'transcript' in results:
                    return True
                else:
                    return False
            except Exception:
                return False
        else:
            start = file_prefix.string_io().read(500).strip()
            if start:
                return "\"media\":" in start and "\"results\":" in start and "\"transcript\":" in start 
            return False
       
@build_sniff_from_prefix
class Ner(AmpJson):
    file_ext = "ner"
    label = "AMP NER JSON"
    
    def _looks_like_json(self, file_prefix):
        # Pattern used by SequenceSplitLocations
        if file_prefix.file_size < 50000 and not file_prefix.truncated:
            # If the file is small enough - don't guess just check.
            try:
                # exclude simple types, must set format in these cases
                item = json.loads(file_prefix.contents_header)
                assert isinstance(item, (list, dict))
                if 'entities' in item and 'media' in item:
                    return True
                else:
                    return False
            except Exception:
                return False
        else:
            start = file_prefix.string_io().read(500).strip()
            if start:
                return "\"media\":" in start and "\"entities\":" in start
            return False
 
@build_sniff_from_prefix
class Shot(AmpJson):
    file_ext = "shot"
    label = "AMP Shot JSON"

    def _looks_like_json(self, file_prefix):
        # Pattern used by SequenceSplitLocations
        if file_prefix.file_size < 50000 and not file_prefix.truncated:
            # If the file is small enough - don't guess just check.
            try:
                # exclude simple types, must set format in these cases
                item = json.loads(file_prefix.contents_header)
                assert isinstance(item, (list, dict))
                if 'shots' in item and 'media' in item:
                    return True
                else:
                    return False
            except Exception:
                return False
        else:
            start = file_prefix.string_io().read(500).strip()
            if start:
                return "\"media\":" in start and "\"shots\":" in start
            return False
           
@build_sniff_from_prefix
class VideoOcr(AmpJson):
    file_ext = "vocr"
    label = "AMP Video OCR JSON"

    def _looks_like_json(self, file_prefix):
        # Pattern used by SequenceSplitLocations
        if file_prefix.file_size < 50000 and not file_prefix.truncated:
            # If the file is small enough - don't guess just check.
            try:
                # exclude simple types, must set format in these cases
                item = json.loads(file_prefix.contents_header)
                assert isinstance(item, (list, dict))
                if not ('frames' in item and 'media' in item):
                    return False                
                frames = item['frames']
                if len(frames) > 0 and 'objects' in frames[0]:
                    objects = frames[0]['objects']
                    if len(objects) > 0 and 'text' in objects[0]:
                        return True
                    else:
                        return False
                else:
                    return False
            except Exception:
                return False
        else:
            start = file_prefix.string_io().read(500).strip()
            if start:
                return "\"media\":" in start and "\"frames\":" in start and "\"objects\":" in start and "\"text\":" in start
            return False    

# Note that the schema for VideoOcr and Face are very similar, except that the former contains "text" while the latter contains "name"
# If there is no frame or no objects in a frame then we can't tell the two types apart, and the sniffer may fall back to JSON.
   
@build_sniff_from_prefix
class Face(AmpJson):
    file_ext = "face"
    label = "AMP Face JSON"

    def _looks_like_json(self, file_prefix):
        # Pattern used by SequenceSplitLocations
        if file_prefix.file_size < 50000 and not file_prefix.truncated:
            # If the file is small enough - don't guess just check.
            try:
                # exclude simple types, must set format in these cases
                item = json.loads(file_prefix.contents_header)
                assert isinstance(item, (list, dict))
                if not ('frames' in item and 'media' in item):
                    return False                
                frames = item['frames']
                if len(frames) > 0 and 'objects' in frames[0]:
                    objects = frames[0]['objects']
                    if len(objects) > 0 and 'name' in objects[0]:
                        return True
                    else:
                        return False
                else:
                    return False
            except Exception:
                return False
        else:
            start = file_prefix.string_io().read(500).strip()
            if start:
                return "\"media\":" in start and "\"frames\":" in start and "\"objects\":" in start and "\"name\":" in start
            return False
           
@build_sniff_from_prefix
class Vtt(Text):
    file_ext = "vtt"
    label = "Web VTT"

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = self.label
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def get_mime(self):
        """Returns the mime type of the datatype"""
        return 'text/vtt'

    def sniff_prefix(self, file_prefix):
        # WEBVTT is the header of a WebVTT file. 
        # We assume that no other kind of text files use this as the first line content; otherwise further checking  
        # on following lines can be done to detect if they match the regexp patterns for timestamp & speaker diarization.
        try:
            first_line = file_prefix.string_io().readline().strip()      
            log.debug ("Vtt.sniff_prefix: first_line = " + first_line)  
            if (first_line == "WEBVTT"):
                log.debug ("Vtt.sniff_prefix: return true")  
                return True
            else:
                log.debug ("Vtt.sniff_prefix: return false")  
                return False
        except Exception as e:
            log.exception(e)
            return False              

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return self.label + " file (%s)" % (nice_size(dataset.get_size()))
