"""Video classes"""

import json
import subprocess
import wave
from functools import lru_cache
from typing import (
    List,
    Tuple,
)

from galaxy.datatypes.binary import Binary
from galaxy.datatypes.metadata import (
    ListParameter,
    MetadataElement,
)
from galaxy.datatypes.protocols import DatasetProtocol
from galaxy.util import which


@lru_cache(maxsize=128)
def _ffprobe(path):
    return subprocess.run(
        ["ffprobe", "-loglevel", "quiet", "-show_format", "-show_streams", "-of", "json", path], capture_output=True
    )


def ffprobe(path):
    completed_process = _ffprobe(path)
    completed_process.check_returncode()
    data = json.loads(completed_process.stdout.decode("utf-8"))
    return data["format"], data["streams"]


magic_number = {
    "mp4": {
        "offset": 4,
        "hex": [
            "66 74 79 70 69",
            "66 74 79 70 6D",
            "66 74 79 70 4D",
        ],
    },
    "flv": {"offset": 0, "hex": ["46 4C 56 01"]},
    "mkv": {"offset": 0, "hex": ["1A 45 DF A3"]},
    "webm": {"offset": 0, "hex": ["1A 45 DF A3"]},
    "mov": {"offset": 4, "hex": ["66 74 79 70 71", "6D 6F 6F 76"]},
    "wav": {"offset": 8, "hex": ["57 41 56 45"]},
    "mp3": {
        "offset": 0,
        "hex": [
            "49 44 33",
            "FF E0",
            "FF E1",
            "FF E2",
            "FF E3",
            "FF E4",
            "FF E5",
            "FF E6",
            "FF E7",
            "FF E8",
            "FF E9",
            "FF EA",
            "FF EB",
            "FF EC",
            "FF ED",
            "FF EE",
            "FF EF",
            "FF F0",
            "FF F1",
            "FF F2",
            "FF F3",
            "FF F4",
            "FF F5",
            "FF F6",
            "FF F7",
            "FF F8",
            "FF F9",
            "FF FA",
            "FF FB",
            "FF FC",
            "FF FD",
            "FF FE",
            "FF FF",
        ],
    },
    "ogg": {"offset": 0, "hex": ["4F 67 67"]},
    "wma": {"offset": 0, "hex": ["30 26 B2 75"]},
    "wmv": {"offset": 0, "hex": ["30 26 B2 75"]},
    "avi": {"offset": 8, "hex": ["41 56 49"]},
    "mpeg": {
        "offset": 0,
        "hex": [
            "00 00 01 B0",
            "00 00 01 B1",
            "00 00 01 B3",
            "00 00 01 B4",
            "00 00 01 B5",
            "00 00 01 B6",
            "00 00 01 B7",
            "00 00 01 B8",
            "00 00 01 B9",
            "00 00 01 BA",
            "00 00 01 BB",
            "00 00 01 BC",
            "00 00 01 BD",
            "00 00 01 BE",
            "00 00 01 BF",
        ],
    },
}


def file_format(filename: str, ff: str):
    with open(filename, "rb") as f:
        f.seek(magic_number[ff]["offset"])
        head = f.read(8)
        return any(head.startswith(bytes.fromhex(hex_code)) for hex_code in magic_number[ff]["hex"])


class Audio(Binary):
    MetadataElement(
        name="duration",
        default=0,
        desc="Length of audio sample",
        readonly=True,
        visible=True,
        optional=True,
        no_value=0,
    )
    MetadataElement(
        name="audio_codecs",
        default=[],
        desc="Audio codec(s)",
        param=ListParameter,
        readonly=True,
        visible=True,
        optional=True,
        no_value=[],
    )
    MetadataElement(
        name="sample_rates",
        default=[],
        desc="Sampling Rate(s)",
        param=ListParameter,
        readonly=True,
        visible=True,
        optional=True,
        no_value=[],
    )
    MetadataElement(
        name="audio_streams",
        default=0,
        desc="Number of audio streams",
        readonly=True,
        visible=True,
        optional=True,
        no_value=0,
    )

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        if which("ffprobe"):
            metadata, streams = ffprobe(dataset.get_file_name())

            dataset.metadata.duration = metadata["duration"]
            dataset.metadata.audio_codecs = [
                stream["codec_name"] for stream in streams if stream["codec_type"] == "audio"
            ]
            dataset.metadata.sample_rates = [
                stream["sample_rate"] for stream in streams if stream["codec_type"] == "audio"
            ]
            dataset.metadata.audio_streams = len([stream for stream in streams if stream["codec_type"] == "audio"])


class Video(Binary):
    MetadataElement(
        name="resolution_w",
        default=0,
        desc="Width of video stream",
        readonly=True,
        visible=True,
        optional=True,
        no_value=0,
    )
    MetadataElement(
        name="resolution_h",
        default=0,
        desc="Height of video stream",
        readonly=True,
        visible=True,
        optional=True,
        no_value=0,
    )
    MetadataElement(
        name="fps", default=0, desc="FPS of video stream", readonly=True, visible=True, optional=True, no_value=0
    )
    MetadataElement(
        name="video_codecs",
        default=[],
        desc="Video codec(s)",
        param=ListParameter,
        readonly=True,
        visible=True,
        optional=True,
        no_value=[],
    )
    MetadataElement(
        name="audio_codecs",
        default=[],
        desc="Audio codec(s)",
        param=ListParameter,
        readonly=True,
        visible=True,
        optional=True,
        no_value=[],
    )
    MetadataElement(
        name="video_streams",
        default=0,
        desc="Number of video streams",
        readonly=True,
        visible=True,
        optional=True,
        no_value=0,
    )
    MetadataElement(
        name="audio_streams",
        default=0,
        desc="Number of audio streams",
        readonly=True,
        visible=True,
        optional=True,
        no_value=0,
    )

    def _get_resolution(self, streams: List) -> Tuple[int, int, float]:
        for stream in streams:
            if stream["codec_type"] == "video":
                w = stream["width"]
                h = stream["height"]
                dividend, divisor = stream["avg_frame_rate"].split("/")
                fps = float(dividend) / float(divisor)
        else:
            w = h = fps = 0
        return w, h, fps

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        if which("ffprobe"):
            metadata, streams = ffprobe(dataset.get_file_name())
            (w, h, fps) = self._get_resolution(streams)
            dataset.metadata.resolution_w = w
            dataset.metadata.resolution_h = h
            dataset.metadata.fps = fps

            dataset.metadata.audio_codecs = [
                stream["codec_name"] for stream in streams if stream["codec_type"] == "audio"
            ]
            dataset.metadata.video_codecs = [
                stream["codec_name"] for stream in streams if stream["codec_type"] == "video"
            ]

            dataset.metadata.audio_streams = len([stream for stream in streams if stream["codec_type"] == "audio"])
            dataset.metadata.video_streams = len([stream for stream in streams if stream["codec_type"] == "video"])


class Mkv(Video):
    file_ext = "mkv"

    def sniff(self, filename: str) -> bool:
        if which("ffprobe"):
            metadata, streams = ffprobe(filename)
            vp_check = any(
                stream["codec_name"] in ["vp8", "vp9"] for stream in streams if stream["codec_type"] == "video"
            )
            return file_format(filename, "mkv") and not vp_check
        return False


class Mp4(Video):
    """
    Class that reads MP4 video file.
    >>> from galaxy.datatypes.sniff import sniff_with_cls
    >>> sniff_with_cls(Mp4, 'video_1.mp4')
    True
    """

    file_ext = "mp4"

    def sniff(self, filename: str) -> bool:
        return file_format(filename, "mp4")


class Flv(Video):
    file_ext = "flv"

    def sniff(self, filename: str) -> bool:
        return file_format(filename, "flv")


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

    def sniff(self, filename: str) -> bool:
        return file_format(filename, "mp3")


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

    MetadataElement(name="rate", desc="Sample Rate", default=0, no_value=0, readonly=True, visible=True, optional=True)
    MetadataElement(
        name="nframes", desc="Number of Samples", default=0, no_value=0, readonly=True, visible=True, optional=True
    )
    MetadataElement(
        name="nchannels", desc="Number of Channels", default=0, no_value=0, readonly=True, visible=True, optional=True
    )
    MetadataElement(
        name="sampwidth", desc="Sample Width", default=0, no_value=0, readonly=True, visible=True, optional=True
    )

    def get_mime(self) -> str:
        """Returns the mime type of the datatype."""
        return "audio/wav"

    def sniff(self, filename: str) -> bool:
        return file_format(filename, "wav")

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        """Set the metadata for this dataset from the file contents."""
        try:
            with wave.open(dataset.dataset.get_file_name(), "rb") as fd:
                dataset.metadata.rate = fd.getframerate()
                dataset.metadata.nframes = fd.getnframes()
                dataset.metadata.sampwidth = fd.getsampwidth()
                dataset.metadata.nchannels = fd.getnchannels()
        except wave.Error:
            pass


class Ogg(Audio):
    file_ext = "ogg"

    def sniff(self, filename: str) -> bool:
        return file_format(filename, "ogg")


class Webm(Video):
    file_ext = "webm"

    def sniff(self, filename: str) -> bool:
        if which("ffprobe"):
            metadata, streams = ffprobe(filename)
            vp_check = any(
                stream["codec_name"] in ["vp8", "vp9"] for stream in streams if stream["codec_type"] == "video"
            )
            return file_format(filename, "webm") and vp_check
        return False


class Mpeg(Video):
    file_ext = "mpeg"

    def sniff(self, filename: str) -> bool:
        return file_format(filename, "mpeg")


class Mov(Video):
    file_ext = "mov"

    def sniff(self, filename: str) -> bool:
        return file_format(filename, "mov")


class Avi(Video):
    file_ext = "avi"

    def sniff(self, filename: str) -> bool:
        return file_format(filename, "avi")


class Wmv(Video):
    file_ext = "wmv"

    def sniff(self, filename: str) -> bool:
        if which("ffprobe"):
            metadata, streams = ffprobe(filename)
            is_video = "video" in [stream["codec_type"] for stream in streams]
            return file_format(filename, "wmv") and is_video
        return False


class Wma(Audio):
    file_ext = "wma"

    def sniff(self, filename: str) -> bool:
        if which("ffprobe"):
            metadata, streams = ffprobe(filename)
            is_audio = "video" not in [stream["codec_type"] for stream in streams]
            return file_format(filename, "wma") and is_audio
        return False
