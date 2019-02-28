"""Audio and video classes"""

from galaxy.datatypes.binary import Binary


class WAV(Binary):
    """Class that reads WAV audio file

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('audio_1.wav')
    >>> WAV().sniff(fname)
    True
    >>> fname = get_test_fname('audio_2.mp3')
    >>> WAV().sniff(fname)
    False
    """

    file_ext = "wav"

    def sniff(self, filename):
        try:
            header = open(filename, 'rb').read(4)
            if header == b'RIFF':
                return True
            return False
        except Exception:
            return False


class Mp3(Binary):
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
        try:
            header = open(filename, 'rb').read(3)
            if header == b'ID3' or header == b'\xff\xfb\x90':
                return True
            return False
        except Exception:
            return False


class Mp4(Binary):
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
        try:
            header = open(filename, 'rb').read(3)
            if header == b'\x00\x00\x00':
                return True
            return False
        except Exception:
            return False
