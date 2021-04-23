

from galaxy.datatypes.media import Audio


###########################
# AMP extended media types
###########################

# class AudioVideo(Binary):
#     """Class describing an audio/video binary file"""
#     file_ext = "av"
#     label = "Audio/Video"
# 
#     def sniff(self, filename):
#         mt = subprocess.check_output(['file', '--mime-type', filename])
#         return  mt.find("audio/")>=0 or mt.find("video/")>=0
#     
#     def set_peek(self, dataset, is_multi_byte=False):
#         if not dataset.dataset.purged:
#             dataset.peek = label
#             dataset.blurb = nice_size(dataset.get_size())
#         else:
#             dataset.peek = 'file does not exist'
#             dataset.blurb = 'file purged from disk'
# 
#     def display_peek(self, dataset):
#         try:
#             return dataset.peek
#         except Exception:
#             return self.label + " file (%s)" % (nice_size(dataset.get_size()))
#
# class Audio(AudioVideo):
#     """Class describing an audio file"""
#     file_ext = "audio"
#     label = "Audio"
# 
#     def sniff(self, filename):
#         mt = subprocess.check_output(['file', '--mime-type', filename])
#         return  mt.find("audio/")>=0
# 
# class Video(AudioVideo):
#     """Class describing a video file"""
#     file_ext = "video"
#     label = "Video"
# 
#     def sniff(self, filename):
#         mt = subprocess.check_output(['file', '--mime-type', filename])
#         return  mt.find("video/")>=0
# 
# class Wav(Audio):
#     """Class describing a WAV audio file"""
#     file_ext = "wav"
#     label = "WAV"
# 
#     def sniff(self, filename):
#         mt = subprocess.check_output(['file', '--mime-type', filename])
#         return  mt.find("audio/wave")>=0 or mt.find("audio/wav")>=0 or mt.find("audio/x-wav")>=0 or mt.find("audio/x-pn-wav")>=0


class Music(Wav):
    """Class describing an AMP music WAV file"""
    file_ext = "music"
    label = "AMP Music WAV"

class Speech(Wav):
    """Class describing an AMP speech WAV file"""
    file_ext = "speech"
    label = "AMP Speech WAV"


