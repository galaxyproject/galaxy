"""Audio and video classes"""
import wave

from galaxy.datatypes.binary import Binary


class WAV( Binary ):
    """RIFF WAV audio file"""

    file_ext = "wav"

    def sniff(self, filename):
        try:
            fp = wave.open(filename, 'rb')
            fp.close()
            return True
        except wave.Error:
            return False
