"""Audio and video classes"""

from galaxy.datatypes.binary import Binary


class WAV(Binary):
    """WAV audio file"""

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
    """MP3 audio file"""

    file_ext = "mp3"

    def sniff(self, filename):
        try:
            header = open(filename, 'rb').read(3)
            if header == b'ID3':
                return True
            return False
        except Exception:
            return False


class Mp4(Binary):
    """MP4 video file"""

    file_ext = "mp4"

    def sniff(self, filename):
        try:
            header = open(filename, 'rb').read(3)
            if header == b'\x00\x00\x00':
                return True
            return False
        except Exception:
            return False
