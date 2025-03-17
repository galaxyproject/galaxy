"""
Image classes
"""

import base64
import json
import logging
import struct
from typing import (
    Any,
    Dict,
    Iterator,
    List,
    Optional,
    Tuple,
)

import mrcfile
import numpy as np
import tifffile

try:
    import PIL
    import PIL.Image
except ImportError:
    PIL = None  # type: ignore[assignment, unused-ignore]

from galaxy.datatypes.binary import Binary
from galaxy.datatypes.metadata import (
    FileParameter,
    MetadataElement,
)
from galaxy.datatypes.protocols import (
    DatasetProtocol,
    HasExtraFilesAndMetadata,
)
from galaxy.datatypes.sniff import (
    build_sniff_from_prefix,
    FilePrefix,
)
from galaxy.datatypes.text import Html as HtmlFromText
from galaxy.util import nice_size
from galaxy.util.image_util import check_image_type
from . import data
from .xml import GenericXml

log = logging.getLogger(__name__)

# TODO: Uploading image files of various types is supported in Galaxy, but on
# the main public instance, the display_in_upload is not set for these data
# types in datatypes_conf.xml because we do not allow image files to be uploaded
# there.  There is currently no API feature that allows uploading files outside
# of a data library ( where it requires either the upload_paths or upload_directory
# option to be enabled, which is not the case on the main public instance ).  Because
# of this, we're currently safe, but when the api is enhanced to allow other uploads,
# we need to ensure that the implementation is such that image files cannot be uploaded
# to our main public instance.


class Image(data.Data):
    """Class describing an image"""

    edam_data = "data_2968"
    edam_format = "format_3547"
    file_ext = ""

    MetadataElement(
        name="axes",
        desc="Axes of the image data",
        readonly=True,
        visible=True,
        optional=True,
    )

    MetadataElement(
        name="dtype",
        desc="Data type of the image pixels or voxels",
        readonly=True,
        visible=True,
        optional=True,
    )

    MetadataElement(
        name="num_unique_values",
        desc="Number of unique values in the image data (e.g., should be 2 for binary images)",
        readonly=True,
        visible=True,
        optional=True,
    )

    MetadataElement(
        name="width",
        desc="Width of the image (in pixels)",
        readonly=True,
        visible=True,
        optional=True,
    )

    MetadataElement(
        name="height",
        desc="Height of the image (in pixels)",
        readonly=True,
        visible=True,
        optional=True,
    )

    MetadataElement(
        name="channels",
        desc="Number of channels of the image",
        readonly=True,
        visible=True,
        optional=True,
    )

    MetadataElement(
        name="depth",
        desc="Depth of the image (number of slices)",
        readonly=True,
        visible=True,
        optional=True,
    )

    MetadataElement(
        name="frames",
        desc="Number of frames in the image sequence (number of time steps)",
        readonly=True,
        visible=True,
        optional=True,
    )

    def __init__(self, **kwd):
        super().__init__(**kwd)
        self.image_formats = [self.file_ext.upper()]

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            dataset.peek = f"Image in {dataset.extension} format"
            dataset.blurb = nice_size(dataset.get_size())
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def sniff(self, filename: str) -> bool:
        """Determine if the file is in this format"""
        return check_image_type(filename, self.image_formats)

    def handle_dataset_as_image(self, hda: DatasetProtocol) -> str:
        dataset = hda.dataset
        name = hda.name or ""
        with open(dataset.get_file_name(), "rb") as f:
            base64_image_data = base64.b64encode(f.read()).decode("utf-8")
        return f"![{name}](data:image/{self.file_ext};base64,{base64_image_data})"

    def set_meta(
        self, dataset: DatasetProtocol, overwrite: bool = True, metadata_tmp_files_dir: Optional[str] = None, **kwd
    ) -> None:
        """
        Try to populate the metadata of the image using a generic image loading library (pillow), if available.

        If an image has two axes, they are assumed to be ``YX``. If an image has three axes, they are assumed to be ``YXC``.
        """
        if PIL is not None:
            try:
                with PIL.Image.open(dataset.get_file_name()) as im:

                    # Determine the metadata values that are available without loading the image data
                    dataset.metadata.width = im.size[1]
                    dataset.metadata.height = im.size[0]
                    dataset.metadata.depth = 0
                    dataset.metadata.frames = getattr(im, "n_frames", 0)
                    dataset.metadata.num_unique_values = sum(val > 0 for val in im.histogram())

                    # Peek into a small 2x2 section of the image data
                    im_peek_arr = np.array(im.crop((0, 0, min((2, im.size[1])), min((2, im.size[0])))))

                    # Determine the remaining metadata values
                    dataset.metadata.dtype = str(im_peek_arr.dtype)
                    if im_peek_arr.ndim == 2:
                        dataset.metadata.axes = "YX"
                        dataset.metadata.channels = 0
                    elif im_peek_arr.ndim == 3:
                        dataset.metadata.axes = "YXC"
                        dataset.metadata.channels = im_peek_arr.shape[2]

            except PIL.UnidentifiedImageError:
                pass


class Jpg(Image):
    edam_format = "format_3579"
    file_ext = "jpg"

    def __init__(self, **kwd):
        super().__init__(**kwd)
        self.image_formats = ["JPEG"]


class Png(Image):
    edam_format = "format_3603"
    file_ext = "png"


class Tiff(Image):
    edam_format = "format_3591"
    file_ext = "tiff"
    MetadataElement(
        name="offsets",
        desc="Offsets File",
        param=FileParameter,
        file_ext="json",
        readonly=True,
        visible=False,
        optional=True,
    )

    def set_meta(
        self, dataset: DatasetProtocol, overwrite: bool = True, metadata_tmp_files_dir: Optional[str] = None, **kwd
    ) -> None:
        """
        Populate the metadata of the TIFF image using the tifffile library.
        """
        spec_key = "offsets"
        if hasattr(dataset.metadata, spec_key):
            offsets_file = dataset.metadata.offsets
            if not offsets_file:
                offsets_file = dataset.metadata.spec[spec_key].param.new_file(
                    dataset=dataset, metadata_tmp_files_dir=metadata_tmp_files_dir
                )
        else:
            offsets_file = None
        try:
            with tifffile.TiffFile(dataset.get_file_name()) as tif:
                offsets = [page.offset for page in tif.pages]

                # Aggregate a list of values for each metadata field (one value for each page of the TIFF file)
                metadata: Dict[str, List[Any]] = {
                    key: []
                    for key in [
                        "axes",
                        "dtype",
                        "width",
                        "height",
                        "channels",
                        "depth",
                        "frames",
                        "num_unique_values",
                    ]
                }

                # TIFF files can contain multiple images, each represented by a series of pages
                for series in tif.series:

                    # Determine the metadata values that should be generally available
                    metadata["axes"].append(series.axes.upper())
                    metadata["dtype"].append(str(series.dtype))

                    axes = metadata["axes"][-1].replace("S", "C")
                    metadata["width"].append(Tiff._get_axis_size(series.shape, axes, "X"))
                    metadata["height"].append(Tiff._get_axis_size(series.shape, axes, "Y"))
                    metadata["channels"].append(Tiff._get_axis_size(series.shape, axes, "C"))
                    metadata["depth"].append(Tiff._get_axis_size(series.shape, axes, "Z"))
                    metadata["frames"].append(Tiff._get_axis_size(series.shape, axes, "T"))

                    # Determine the metadata values that require reading the image data
                    metadata["num_unique_values"].append(Tiff._get_num_unique_values(series))

                # Populate the metadata fields based on the values determined above
                for key, values in metadata.items():
                    if len(values) > 0:

                        # Populate as plain value, if there is just one value, and as a list otherwise
                        if len(values) == 1:
                            setattr(dataset.metadata, key, values[0])
                        else:
                            setattr(dataset.metadata, key, values)

            # Populate the "offsets" file and metadata field
            if offsets_file:
                with open(offsets_file.get_file_name(), "w") as f:
                    json.dump(offsets, f)
                dataset.metadata.offsets = offsets_file

        # Catch errors from deep inside the tifffile library
        except (
            AttributeError,
            IndexError,
            KeyError,
            OSError,
            RuntimeError,
            struct.error,
            tifffile.OmeXmlError,
            tifffile.TiffFileError,
            TypeError,
            ValueError,
        ):
            pass

    @staticmethod
    def _get_axis_size(shape: Tuple[int, ...], axes: str, axis: str) -> int:
        idx = axes.find(axis)
        return shape[idx] if idx >= 0 else 0

    @staticmethod
    def _get_num_unique_values(series: tifffile.TiffPageSeries) -> int:
        """
        Determines the number of unique values in a TIFF series of pages.
        """
        unique_values = []
        try:
            for page in series.pages:
                for chunk in Tiff._read_chunks(page):
                    unique_values = list(np.unique(unique_values + list(chunk)))
            return len(unique_values)
        except ValueError:
            return None  # Occurs if the compression of the TIFF file is unsupported

    @staticmethod
    def _read_chunks(page: tifffile.TiffPage, mmap_chunk_size: int = 2 ** 14) -> Iterator[np.ndarray]:
        """
        Generator that reads all chunks of values from a TIFF page.
        """
        is_tiled = (len(page.dataoffsets) > 1)
        unique_values = []
        if is_tiled:

            # There are multiple segments that can be processed consecutively
            for segment in Tiff._read_segments(page):
                yield segment.reshape(-1)

        else:

            # The page can be memory-mapped and processed chunk-wise
            arr = page.asarray(out='memmap')  # No considerable amounts of memory should be allocated here
            arr_flat = arr.reshape(-1)  # This should only produce a view without any new allocations
            if mmap_chunk_size > len(arr_flat):
                yield arr_flat
            else:
                for chunk in np.array_split(arr_flat, mmap_chunk_size):
                    yield chunk

    @staticmethod
    def _read_segments(page: tifffile.TiffPage) -> Iterator[np.ndarray]:
        """
        Generator that reads all segments of a TIFF page.
        """
        reader = page.parent.filehandle
        for segment_idx, (segment_offset, segment_size) in enumerate(zip(page.dataoffsets, page.databytecounts)):
            reader.seek(segment_offset)
            segment_data = reader.read(segment_size)
            yield page.decode(segment_data, segment_idx)[0]

    def sniff(self, filename: str) -> bool:
        with tifffile.TiffFile(filename):
            return True


class OMETiff(Tiff):
    file_ext = "ome.tiff"

    def sniff(self, filename: str) -> bool:
        with tifffile.TiffFile(filename) as tif:
            if tif.is_ome:
                return True
        return False


class OMEZarr(data.ZarrDirectory):
    """OME-Zarr is a format for storing multi-dimensional image data in Zarr format.

    It is technically a Zarr directory with custom metadata but stores image information
    so it is an Image datatype.
    """

    file_ext = "ome_zarr"

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            dataset.peek = "OME-Zarr directory"
            dataset.blurb = f"Zarr Format v{dataset.metadata.zarr_format}"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"


class Hamamatsu(Image):
    file_ext = "vms"


class Mirax(Image):
    file_ext = "mrxs"


class Sakura(Image):
    file_ext = "svslide"


class Nrrd(Image):
    file_ext = "nrrd"


class Bmp(Image):
    edam_format = "format_3592"
    file_ext = "bmp"


class Gif(Image):
    edam_format = "format_3467"
    file_ext = "gif"


class Im(Image):
    edam_format = "format_3593"
    file_ext = "im"


class Pcd(Image):
    edam_format = "format_3594"
    file_ext = "pcd"


class Pcx(Image):
    edam_format = "format_3595"
    file_ext = "pcx"


class Ppm(Image):
    edam_format = "format_3596"
    file_ext = "ppm"


class Psd(Image):
    edam_format = "format_3597"
    file_ext = "psd"


class Xbm(Image):
    edam_format = "format_3598"
    file_ext = "xbm"


class Xpm(Image):
    edam_format = "format_3599"
    file_ext = "xpm"


class Rgb(Image):
    edam_format = "format_3600"
    file_ext = "rgb"


class Pbm(Image):
    edam_format = "format_3601"
    file_ext = "pbm"


class Pgm(Image):
    edam_format = "format_3602"
    file_ext = "pgm"


class Eps(Image):
    edam_format = "format_3466"
    file_ext = "eps"


class Rast(Image):
    edam_format = "format_3605"
    file_ext = "rast"


class Pdf(Image):
    edam_format = "format_3508"
    file_ext = "pdf"

    def sniff(self, filename: str) -> bool:
        """Determine if the file is in pdf format."""
        with open(filename, "rb") as fh:
            return fh.read(4) == b"%PDF"


@build_sniff_from_prefix
class Tck(Binary):
    """
    Tracks file format (.tck) format
    https://mrtrix.readthedocs.io/en/latest/getting_started/image_data.html#tracks-file-format-tck

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('fibers_sparse_top_6_lines.tck')
    >>> Tck().sniff( fname )
    True
    >>> fname = get_test_fname('2.txt')
    >>> Tck().sniff( fname )
    False
    """

    file_ext = "tck"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        format_def = [
            [b"mrtrix tracks"],
            [b"datatype: Float32LE", b"datatype: Float32BE", b"datatype: Float64BE", b"datatype: Float64LE"],
            [b"count: "],
            [b"file: ."],
            [b"END"],
        ]
        matches = 0

        for elem in format_def:
            for identifier in elem:
                if identifier in file_prefix.contents_header_bytes:
                    matches += 1
        if matches == 5:
            return True
        return False


@build_sniff_from_prefix
class Trk(Binary):
    """
    Track File format (.trk) is the tractography file format.
    http://trackvis.org/docs/?subsect=fileformat

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('IIT2mean_top_2000bytes.trk')
    >>> Trk().sniff( fname )
    True
    >>> fname = get_test_fname('2.txt')
    >>> Trk().sniff( fname )
    False
    """

    file_ext = "trk"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        # quick check
        header_raw = None
        header_raw = file_prefix.contents_header_bytes[:1000]

        if header_raw[:5] != b"TRACK":
            return False
        # detailed check
        header_def = [
            ("magic", "S6"),
            ("dim", "h", 3),
            ("voxel_size", "f4", 3),
            ("origin", "f4", 3),
            ("n_scalars", "h"),
            ("scalar_name", "S20", 10),
            ("n_properties", "h"),
            ("property_name", "S20", 10),
            ("vox_to_ras", "f4", (4, 4)),
            ("reserved", "S444"),
            ("voxel_order", "S4"),
            ("pad2", "S4"),
            ("image_orientation_patient", "f4", 6),
            ("pad1", "S2"),
            ("invert_x", "S1"),
            ("invert_y", "S1"),
            ("invert_z", "S1"),
            ("swap_xy", "S1"),
            ("swap_yz", "S1"),
            ("swap_zx", "S1"),
            ("n_count", "i4"),
            ("version", "i4"),
            ("header_size", "i4"),
        ]
        np_dtype = np.dtype(header_def)
        header: np.ndarray = np.ndarray(shape=(), dtype=np_dtype, buffer=header_raw)
        if (
            header["header_size"] == 1000
            and b"TRACK" in header["magic"]
            and header["version"] == 2
            and len(header["dim"]) == 3
        ):
            return True
        return False


class Mrc2014(Binary):
    """
    MRC/CCP4 2014 file format (.mrc).
    https://www.ccpem.ac.uk/mrc_format/mrc2014.php

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('1.mrc')
    >>> Mrc2014().sniff(fname)
    True
    >>> fname = get_test_fname('2.txt')
    >>> Mrc2014().sniff(fname)
    False
    """

    file_ext = "mrc"

    def sniff(self, filename: str) -> bool:
        try:
            # An exception is thrown
            # if the file is not an
            # mrc2014 file.
            mrcfile.load_functions.open(filename, header_only=True)
            return True
        except Exception:
            return False


class Gmaj(data.Data):
    """Deprecated class. Exists for limited backwards compatibility."""

    edam_format = "format_3547"
    file_ext = "gmaj.zip"

    def get_mime(self) -> str:
        """Returns the mime type of the datatype"""
        return "application/zip"


class Analyze75(Binary):
    """
    Mayo Analyze 7.5 files
    http://www.imzml.org
    """

    file_ext = "analyze75"
    composite_type = "auto_primary_file"

    def __init__(self, **kwd):
        super().__init__(**kwd)

        # The header file provides information about dimensions, identification,
        # and processing history.
        self.add_composite_file("hdr", description="The Analyze75 header file.", is_binary=True)

        # The image file contains the actual data, whose data type and ordering
        # are described by the header file.
        self.add_composite_file("img", description="The Analyze75 image file.", is_binary=True)

        self.add_composite_file("t2m", description="The Analyze75 t2m file.", optional=True, is_binary=True)

    def generate_primary_file(self, dataset: HasExtraFilesAndMetadata) -> str:
        rval = ["<html><head><title>Analyze75 Composite Dataset.</title></head><p/>"]
        rval.append("<div>This composite dataset is composed of the following files:<p/><ul>")
        for composite_name, composite_file in self.get_composite_files(dataset=dataset).items():
            fn = composite_name
            opt_text = ""
            if composite_file.optional:
                opt_text = " (optional)"
            if composite_file.get("description"):
                rval.append(
                    f"<li><a href=\"{fn}\" type=\"text/plain\">{fn} ({composite_file.get('description')})</a>{opt_text}</li>"
                )
            else:
                rval.append(f'<li><a href="{fn}" type="text/plain">{fn}</a>{opt_text}</li>')
        rval.append("</ul></div></html>")
        return "\n".join(rval)


@build_sniff_from_prefix
class Nifti1(Binary):
    """
    Nifti1 format
    https://nifti.nimh.nih.gov/pub/dist/src/niftilib/nifti1.h

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('T1_top_350bytes.nii1')
    >>> Nifti1().sniff( fname )
    True
    >>> fname = get_test_fname('2.txt')
    >>> Nifti1().sniff( fname )
    False
    """

    file_ext = "nii1"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        magic = file_prefix.contents_header_bytes[344:348]
        if magic == b"n+1\0":
            return True
        return False


@build_sniff_from_prefix
class Nifti2(Binary):
    """
    Nifti2 format
    https://brainder.org/2015/04/03/the-nifti-2-file-format/

    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('avg152T1_LR_nifti2_top_100bytes.nii2')
    >>> Nifti2().sniff( fname )
    True
    >>> fname = get_test_fname('T1_top_350bytes.nii1')
    >>> Nifti2().sniff( fname )
    False
    """

    file_ext = "nii2"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        magic = file_prefix.contents_header_bytes[4:8]
        if magic in [b"n+2\0", b"ni2\0"]:
            return True
        return False


@build_sniff_from_prefix
class Gifti(GenericXml):
    """Class describing a Gifti format"""

    file_ext = "gii"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """Determines whether the file is a Gifti file

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('Human.colin.R.activations.label.gii')
        >>> Gifti().sniff(fname)
        True
        >>> fname = get_test_fname('interval.interval')
        >>> Gifti().sniff(fname)
        False
        >>> fname = get_test_fname('megablast_xml_parser_test1.blastxml')
        >>> Gifti().sniff(fname)
        False
        >>> fname = get_test_fname('tblastn_four_human_vs_rhodopsin.blastxml')
        >>> Gifti().sniff(fname)
        False
        """
        handle = file_prefix.string_io()
        line = handle.readline()
        if not line.strip().startswith('<?xml version="1.0"'):
            return False
        line = handle.readline()
        if line.strip() == '<!DOCTYPE GIFTI SYSTEM "http://www.nitrc.org/frs/download.php/1594/gifti.dtd">':
            return True
        line = handle.readline()
        if line.strip().startswith("<GIFTI"):
            return True
        return False


@build_sniff_from_prefix
class Star(data.Text):
    """Base format class for Relion STAR (Self-defining
    Text Archiving and Retrieval) image files.
    https://relion.readthedocs.io/en/latest/Reference/Conventions.html"""

    file_ext = "star"

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek(dataset.get_file_name())
            dataset.blurb = "Relion STAR data"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """Each file must have one or more data blocks.
        The start of a data block is defined by the keyword
        ``data_`` followed by an optional string for
        identification (e.g., ``data_images``).  All text
        before the first ``data_`` keyword are comments

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('1.star')
        >>> Star().sniff(fname)
        True
        >>> fname = get_test_fname('interval.interval')
        >>> Star().sniff(fname)
        False
        """
        in_data_block = False
        for line in file_prefix.line_iterator():
            # All lines before the first
            # data_ block must be comments.
            line = line.strip()
            if len(line) == 0:
                continue
            if line.startswith("data_"):
                in_data_block = True
                continue
            if in_data_block:
                # Lines within data blocks must
                # be blank, start with loop_, or
                # start with _.
                if len(line) == 0:
                    continue
                if line.startswith("loop_") or line.startswith("_"):
                    return True
                return False
        return False


class Html(HtmlFromText):
    """Deprecated class. This class should not be used anymore, but the galaxy.datatypes.text:Html one.
    This is for backwards compatibilities only."""


class Laj(data.Text):
    """Deprecated class. Exists for limited backwards compatibility."""
