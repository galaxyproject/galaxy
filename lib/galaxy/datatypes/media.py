"""Video classes"""
import json
import subprocess
import wave

from galaxy.datatypes.binary import Binary
from galaxy.datatypes.metadata import ListParameter, MetadataElement


def ffprobe(path):
    data = json.loads(subprocess.check_output(['ffprobe', '-loglevel', 'quiet', '-show_format', '-show_streams', '-of', 'json', path]))
    return data['format'], data['streams']


class Audio(Binary):

    MetadataElement(name="duration", default=0, desc="Length of audio sample", readonly=True, visible=True, optional=True, no_value=0)
    MetadataElement(name="audio_codecs", default=[], desc="Audio codec(s)", param=ListParameter, readonly=True, visible=True, optional=True, no_value=[])
    MetadataElement(name="sample_rates", default=[], desc="Sampling Rate(s)", param=ListParameter, readonly=True, visible=True, optional=True, no_value=[])
    MetadataElement(name="audio_streams", default=0, desc="Number of audio streams", readonly=True, visible=True, optional=True, no_value=0)

    def set_meta(self, dataset, **kwd):
        metadata, streams = ffprobe(dataset.file_name)

        dataset.metadata.duration = metadata['duration']
        dataset.metadata.audio_codecs = [stream['codec_name'] for stream in streams if stream['codec_type'] == 'audio']
        dataset.metadata.sample_rates = [stream['sample_rate'] for stream in streams if stream['codec_type'] == 'audio']
        dataset.metadata.audio_streams = len([stream for stream in streams if stream['codec_type'] == 'audio'])


class Video(Binary):

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
        metadata, streams = ffprobe(dataset.file_name)
        (w, h, fps) = self._get_resolution(streams)
        dataset.metadata.resolution_w = w
        dataset.metadata.resolution_h = h
        dataset.metadata.fps = fps

        dataset.metadata.audio_codecs = [stream['codec_name'] for stream in streams if stream['codec_type'] == 'audio']
        dataset.metadata.video_codecs = [stream['codec_name'] for stream in streams if stream['codec_type'] == 'video']

        dataset.metadata.audio_streams = len([stream for stream in streams if stream['codec_type'] == 'audio'])
        dataset.metadata.video_streams = len([stream for stream in streams if stream['codec_type'] == 'video'])


class Mkv(Video):
    file_ext = "mkv"

    def sniff(self, filename):
        metadata, streams = ffprobe(filename)
        return 'matroska' in metadata['format_name'].split(',')


class Mp4(Video):
    """Class that reads MP4 video file
    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('video_1.mp4')
    >>> Mp4().sniff(fname)
    True
    >>> fname = get_test_fname('audio_1.wav')
    >>> Mp4().sniff(fname)
    False
    """

    file_ext = "mp4"

    def sniff(self, filename):
        metadata, streams = ffprobe(filename)
        return 'mp4' in metadata['format_name'].split(',')


class Flv(Video):
    file_ext = "flv"

    def sniff(self, filename):
        metadata, streams = ffprobe(filename)
        return 'flv' in metadata['format_name'].split(',')


class Mpg(Video):
    file_ext = "mpg"

    def sniff(self, filename):
        metadata, streams = ffprobe(filename)
        return 'mpegvideo' in metadata['format_name'].split(',')


class Mp3(Audio):
    """Class that reads MP3 audio file
    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('audio_2.mp3')
    >>> Mp3().sniff(fname)
    True
    >>> fname = get_test_fname('audio_1.wav')
    >>> Mp3().sniff(fname)
    False
    """
    file_ext = "mp3"

    def sniff(self, filename):
        metadata, streams = ffprobe(filename)
        return 'mp3' in metadata['format_name'].split(',')


class WAV(Binary):
    """Class that reads WAV audio file
    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('hello.wav')
    >>> WAV().sniff(fname)
    True
    >>> fname = get_test_fname('audio_1.wav')
    >>> WAV().sniff(fname)
    True
    >>> fname = get_test_fname('audio_2.mp3')
    >>> WAV().sniff(fname)
    False
    """

    file_ext = "wav"
    blurb = "RIFF WAV Audio file"
    is_binary = True

    MetadataElement(name="rate", desc="Sample Rate", default=0, no_value=0, readonly=True, visible=True, optional=True)
    MetadataElement(name="nframes", desc="Number of Samples", default=0, no_value=0, readonly=True, visible=True, optional=True)
    MetadataElement(name="nchannels", desc="Number of Channels", default=0, no_value=0, readonly=True, visible=True, optional=True)
    MetadataElement(name="sampwidth", desc="Sample Width", default=0, no_value=0, readonly=True, visible=True, optional=True)

    def get_mime(self):
        """Returns the mime type of the datatype"""
        return 'audio/wav'

    def sniff(self, filename):
        """
        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('hello.wav')
        >>> WAV().sniff(fname)
        True

        >>> fname = get_test_fname('drugbank_drugs.cml')
        >>> WAV().sniff(fname)
        False
        """

        try:
            fp = wave.open(filename, 'rb')
            fp.close()
            return True
        except wave.Error:
            return False

    def set_meta(self, dataset, overwrite=True, **kwd):
        """Set the metadata for this dataset from the file contents
        """

        try:
            fd = wave.open(dataset.dataset.file_name, 'rb')
            dataset.metadata.rate = fd.getframerate()
            dataset.metadata.nframes = fd.getnframes()
            dataset.metadata.sampwidth = fd.getsampwidth()
            dataset.metadata.nchannels = fd.getnchannels()
        except wave.Error:
            pass
        finally:
            fd.close()
