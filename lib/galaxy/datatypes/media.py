"""Video classes"""
import json
import subprocess
import wave

from galaxy.datatypes.binary import Binary
from galaxy.datatypes.metadata import ListParameter, MetadataElement
from galaxy.util import which, nice_size    # AMP customization


def ffprobe(path):
    data = json.loads(subprocess.check_output(['ffprobe', '-loglevel', 'quiet', '-show_format', '-show_streams', '-of', 'json', path]).decode("utf-8"))
    return data['format'], data['streams']


# AMP customization
class AudioVideo(Binary):
    """Class describing an audio/video binary file"""
    file_ext = "av"
    label = "Audio/Video"

    def sniff(self, filename):
        mt = subprocess.check_output(['file', '--mime-type', filename])
        return  mt.find("audio/")>=0 or mt.find("video/")>=0
    
    def set_peek(self, dataset, is_multi_byte=False):
        if not dataset.dataset.purged:
            dataset.peek = label
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = 'file does not exist'
            dataset.blurb = 'file purged from disk'

    def display_peek(self, dataset):
        try:
            return dataset.peek
        except Exception:
            return self.label + " file (%s)" % (nice_size(dataset.get_size()))
        

# AMP customization        
class Audio(AudioVideo):
    MetadataElement(name="duration", default=0, desc="Length of audio sample", readonly=True, visible=True, optional=True, no_value=0)
    MetadataElement(name="audio_codecs", default=[], desc="Audio codec(s)", param=ListParameter, readonly=True, visible=True, optional=True, no_value=[])
    MetadataElement(name="sample_rates", default=[], desc="Sampling Rate(s)", param=ListParameter, readonly=True, visible=True, optional=True, no_value=[])
    MetadataElement(name="audio_streams", default=0, desc="Number of audio streams", readonly=True, visible=True, optional=True, no_value=0)

    def set_meta(self, dataset, **kwd):
        if which('ffprobe'):
            metadata, streams = ffprobe(dataset.file_name)

            dataset.metadata.duration = metadata['duration']
            dataset.metadata.audio_codecs = [stream['codec_name'] for stream in streams if stream['codec_type'] == 'audio']
            dataset.metadata.sample_rates = [stream['sample_rate'] for stream in streams if stream['codec_type'] == 'audio']
            dataset.metadata.audio_streams = len([stream for stream in streams if stream['codec_type'] == 'audio'])
            
    # AMP customization START  
    file_ext = "audio"
    label = "Audio"
 
    def sniff(self, filename):
        mt = subprocess.check_output(['file', '--mime-type', filename])
        return  mt.find("audio/")>=0         
    # AMP customization END


# AMP customization
class Video(AudioVideo):
    MetadataElement(name="resolution_w", default=0, desc="Width of video stream", readonly=True, visible=True, optional=True, no_value=0)
    MetadataElement(name="resolution_h", default=0, desc="Height of video stream", readonly=True, visible=True, optional=True, no_value=0)
    MetadataElement(name="fps", default=0, desc="FPS of video stream", readonly=True, visible=True, optional=True, no_value=0)
    MetadataElement(name="video_codecs", default=[], desc="Video codec(s)", param=ListParameter, readonly=True, visible=True, optional=True, no_value=[])
    MetadataElement(name="audio_codecs", default=[], desc="Audio codec(s)", param=ListParameter, readonly=True, visible=True, optional=True, no_value=[])
    MetadataElement(name="video_streams", default=0, desc="Number of video streams", readonly=True, visible=True, optional=True, no_value=0)
    MetadataElement(name="audio_streams", default=0, desc="Number of audio streams", readonly=True, visible=True, optional=True, no_value=0)

    def _get_resolution(self, streams):
        for stream in streams:
            if stream['codec_type'] == 'video':
                w = stream['width']
                h = stream['height']
                dividend, divisor = stream['avg_frame_rate'].split('/')
                fps = float(dividend) / float(divisor)
        else:
            w = h = fps = 0
        return w, h, fps

    def set_meta(self, dataset, **kwd):
        if which('ffprobe'):
            metadata, streams = ffprobe(dataset.file_name)
            (w, h, fps) = self._get_resolution(streams)
            dataset.metadata.resolution_w = w
            dataset.metadata.resolution_h = h
            dataset.metadata.fps = fps

            dataset.metadata.audio_codecs = [stream['codec_name'] for stream in streams if stream['codec_type'] == 'audio']
            dataset.metadata.video_codecs = [stream['codec_name'] for stream in streams if stream['codec_type'] == 'video']

            dataset.metadata.audio_streams = len([stream for stream in streams if stream['codec_type'] == 'audio'])
            dataset.metadata.video_streams = len([stream for stream in streams if stream['codec_type'] == 'video'])

    # AMP customization START
    file_ext = "video"
    label = "Video"
 
    def sniff(self, filename):
        mt = subprocess.check_output(['file', '--mime-type', filename])
        return  mt.find("video/")>=0
    # AMP customization END
    
    
class Mkv(Video):
    file_ext = "mkv"
    label = "MKV Video" # AMP customization

    def sniff(self, filename):
        if which('ffprobe'):
            metadata, streams = ffprobe(filename)
            return 'matroska' in metadata['format_name'].split(',')


class Mp4(Video):
    """
    Class that reads MP4 video file.
    >>> from galaxy.datatypes.sniff import sniff_with_cls
    >>> sniff_with_cls(Mp4, 'video_1.mp4')
    True
    >>> sniff_with_cls(Mp4, 'audio_1.mp4')
    False
    """

    file_ext = "mp4"
    label = "MP4 Video" # AMP customization

    def sniff(self, filename):
        if which('ffprobe'):
            metadata, streams = ffprobe(filename)
            return 'mp4' in metadata['format_name'].split(',')


class Flv(Video):
    file_ext = "flv"
    label = "FLV Video" # AMP customization

    def sniff(self, filename):
        if which('ffprobe'):
            metadata, streams = ffprobe(filename)
            return 'flv' in metadata['format_name'].split(',')


class Mpg(Video):
    file_ext = "mpg"
    label = "MPG Video" # AMP customization

    def sniff(self, filename):
        if which('ffprobe'):
            metadata, streams = ffprobe(filename)
            return 'mpegvideo' in metadata['format_name'].split(',')


class Mp3(Audio):
    """
    Class that reads MP3 audio file.
    >>> from galaxy.datatypes.sniff import sniff_with_cls
    >>> sniff_with_cls(Mp3, 'audio_2.mp3')
    True
    >>> sniff_with_cls(Mp3, 'audio_1.wav')
    False
    """
    file_ext = "mp3"
    label = "MP3 Audio" # AMP customization

    def sniff(self, filename):
        if which('ffprobe'):
            metadata, streams = ffprobe(filename)
            return 'mp3' in metadata['format_name'].split(',')


class Wav(Audio):
    """Class that reads WAV audio file
    >>> from galaxy.datatypes.sniff import sniff_with_cls
    >>> sniff_with_cls(Wav, 'hello.wav')
    True
    >>> sniff_with_cls(Wav, 'audio_2.mp3')
    False
    >>> sniff_with_cls(Wav, 'drugbank_drugs.cml')
    False
    """
    file_ext = "wav"
    blurb = "RIFF WAV Audio file"
    is_binary = True
    label = "WAV Audio" # AMP customization

    MetadataElement(name="rate", desc="Sample Rate", default=0, no_value=0, readonly=True, visible=True, optional=True)
    MetadataElement(name="nframes", desc="Number of Samples", default=0, no_value=0, readonly=True, visible=True, optional=True)
    MetadataElement(name="nchannels", desc="Number of Channels", default=0, no_value=0, readonly=True, visible=True, optional=True)
    MetadataElement(name="sampwidth", desc="Sample Width", default=0, no_value=0, readonly=True, visible=True, optional=True)

    def get_mime(self):
        """Returns the mime type of the datatype."""
        return 'audio/wav'

    def sniff(self, filename):
        with wave.open(filename, 'rb'):
            return True

    def set_meta(self, dataset, overwrite=True, **kwd):
        """Set the metadata for this dataset from the file contents."""
        try:
            with wave.open(dataset.dataset.file_name, 'rb') as fd:
                dataset.metadata.rate = fd.getframerate()
                dataset.metadata.nframes = fd.getnframes()
                dataset.metadata.sampwidth = fd.getsampwidth()
                dataset.metadata.nchannels = fd.getnchannels()
        except wave.Error:
            pass
