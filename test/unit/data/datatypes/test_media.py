import pytest

from galaxy.datatypes.media import Mp3
from galaxy.datatypes.registry import example_datatype_registry_for_sample
from galaxy.datatypes.sniff import (
    FilePrefix,
    get_test_fname,
    handle_uploaded_dataset_file_internal,
)


@pytest.fixture
def without_ffprobe(monkeypatch):
    monkeypatch.setattr("galaxy.datatypes.media.which", lambda command: None)


@pytest.mark.parametrize("convert_to_posix_lines", [True, False])
def test_utf16_upload_is_not_mp3(tmp_path, without_ffprobe, convert_to_posix_lines):
    content = "Name\tAge\tCity\r\nAlice\t30\tLondon\r\nBob\t25\tNew York\r\nCharlie\t35\tSydney\r\n"
    source = ("\ufeff" + content).encode("utf-16-le")
    path = tmp_path / "example.tsv"
    path.write_bytes(source)

    result = handle_uploaded_dataset_file_internal(
        FilePrefix(str(path)),
        example_datatype_registry_for_sample(),
        convert_to_posix_lines=convert_to_posix_lines,
    )

    assert result.ext == "binary"
    assert result.converted_path == str(path)
    assert not result.converted_newlines
    assert path.read_bytes() == source


@pytest.mark.parametrize("filename,expected", [("audio_2.mp3", True), ("audio_1.wav", False)])
def test_mp3_fallback_fixture(filename, expected, without_ffprobe):
    assert Mp3().sniff(get_test_fname(filename)) is expected


@pytest.mark.parametrize("version", [0b00, 0b01, 0b10, 0b11], ids=["mpeg2.5", "reserved", "mpeg2", "mpeg1"])
@pytest.mark.parametrize("layer", [0b00, 0b01, 0b10, 0b11], ids=["reserved", "layer3", "layer2", "layer1"])
@pytest.mark.parametrize("protection", [0, 1], ids=["crc", "no-crc"])
def test_mp3_fallback_frame_header(tmp_path, without_ffprobe, version, layer, protection):
    path = tmp_path / "audio"
    path.write_bytes(bytes([0xFF, 0xE0 | version << 3 | layer << 1 | protection, 0x90, 0x00]))
    assert Mp3().sniff(str(path)) is (version != 0b01 and layer == 0b01)
