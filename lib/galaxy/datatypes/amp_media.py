from galaxy.datatypes.media import Audio

###########################
# AMP extended media types
###########################

# class AudioVideo(Binary):
#     """Class describing an audio/video binary file"""
#     file_ext = "av"
# 
#     def sniff(self, filename):
#         mt = subprocess.check_output(['file', '--mime-type', filename])
#         return  mt.find("audio/")>=0 or mt.find("video/")>=0
#     
#     def set_peek(self, dataset, is_multi_byte=False):
#         if not dataset.dataset.purged:
#             dataset.peek = "Audio/video binary file"
#             dataset.blurb = nice_size(dataset.get_size())
#         else:
#             dataset.peek = 'file does not exist'
#             dataset.blurb = 'file purged from disk'
# 
#     def display_peek(self, dataset):
#         try:
#             return dataset.peek
#         except Exception:
#             return "Audio/video binary file (%s)" % (nice_size(dataset.get_size()))
#
# class Audio(AudioVideo):
#     """Class describing an audio file"""
#     file_ext = "audio"
# 
#     def sniff(self, filename):
#         mt = subprocess.check_output(['file', '--mime-type', filename])
#         return  mt.find("audio/")>=0
#     
#     def set_peek(self, dataset, is_multi_byte=False):
#         if not dataset.dataset.purged:
#             dataset.peek = "Audio file"
#             dataset.blurb = nice_size(dataset.get_size())
#         else:
#             dataset.peek = 'file does not exist'
#             dataset.blurb = 'file purged from disk'
# 
#     def display_peek(self, dataset):
#         try:
#             return dataset.peek
#         except Exception:
#             return "Audio file (%s)" % (nice_size(dataset.get_size()))
# 
# class Video(AudioVideo):
#     """Class describing a video file"""
#     file_ext = "video"
# 
#     def sniff(self, filename):
#         mt = subprocess.check_output(['file', '--mime-type', filename])
#         return  mt.find("video/")>=0
#     
#     def set_peek(self, dataset, is_multi_byte=False):
#         if not dataset.dataset.purged:
#             dataset.peek = "Video file"
#             dataset.blurb = nice_size(dataset.get_size())
#         else:
#             dataset.peek = 'file does not exist'
#             dataset.blurb = 'file purged from disk'
# 
#     def display_peek(self, dataset):
#         try:
#             return dataset.peek
#         except Exception:
#             return "Video file (%s)" % (nice_size(dataset.get_size()))

class Wav(Audio):
    """Class describing a WAV audio file"""
    file_ext = "wav"

    def sniff(self, filename):
        mt = subprocess.check_output(['file', '--mime-type', filename])
        return  mt.find("audio/wave")>=0 or mt.find("audio/wav")>=0 or mt.find("audio/x-wav")>=0 or mt.find("audio/x-pn-wav")>=0

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = "WAV audio file"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "WAV audio file (%s)" % (nice_size(dataset.get_size()))

class Music(Wav):
    """Class describing an AMP music WAV file"""
    file_ext = "music"

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = "AMP music WAV file"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "AMP music WAV file (%s)" % (nice_size(dataset.get_size()))

class Speech(Wav):
    """Class describing an AMP speech WAV file"""
    file_ext = "speech"

    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = "AMP speech WAV file"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return "AMP speech WAV file (%s)" % (nice_size(dataset.get_size()))

