# TODO: revisit ignoring type and write some tests for this, the multi-inheritance in this
# this file is challenging, it should be broken into true mixins.
"""
Constructive Solid Geometry file formats.
"""

import abc
from typing import (
    List,
    Optional,
    Tuple,
    TYPE_CHECKING,
)

from galaxy import util
from galaxy.datatypes import data
from galaxy.datatypes.binary import Binary
from galaxy.datatypes.data import (
    get_file_peek,
    nice_size,
)
from galaxy.datatypes.metadata import MetadataElement
from galaxy.datatypes.protocols import (
    DatasetProtocol,
    HasMetadata,
)
from galaxy.datatypes.sniff import (
    build_sniff_from_prefix,
    FilePrefix,
)
from galaxy.datatypes.tabular import Tabular
from galaxy.datatypes.xml import GenericXml
from xml.etree import ElementTree as ET

if TYPE_CHECKING:
    from io import TextIOBase

MAX_HEADER_LINES = 500
MAX_LINE_LEN = 2000
COLOR_OPTS = ["COLOR_SCALARS", "red", "green", "blue"]


@build_sniff_from_prefix
class Ply:
    """
    The PLY format describes an object as a collection of vertices,
    faces and other elements, along with properties such as color and
    normal direction that can be attached to these elements.  A PLY
    file contains the description of exactly one object.
    """

    subtype = ""
    # Add metadata elements.
    MetadataElement(name="file_format", default=None, desc="File format", readonly=True, optional=True, visible=True)
    MetadataElement(name="vertex", default=None, desc="Vertex", readonly=True, optional=True, visible=True)
    MetadataElement(name="face", default=None, desc="Face", readonly=True, optional=True, visible=True)
    MetadataElement(
        name="other_elements",
        default=[],
        desc="Other elements",
        readonly=True,
        optional=True,
        visible=True,
        no_value=[],
    )

    @abc.abstractmethod
    def __init__(self, **kwd):
        raise NotImplementedError

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        The structure of a typical PLY file:
        Header, Vertex List, Face List, (lists of other elements)
        """
        if not self._is_ply_header(file_prefix.text_io(errors="ignore"), self.subtype):
            return False
        return True

    def _is_ply_header(self, fh: "TextIOBase", subtype: str) -> bool:
        """
        The header is a series of carriage-return terminated lines of
        text that describe the remainder of the file.
        """
        valid_header_items = ["comment", "obj_info", "element", "property"]
        # Line 1: ply
        line = get_next_line(fh)
        if line != "ply":
            return False
        # Line 2: format ascii 1.0
        line = get_next_line(fh)
        if line.find(subtype) < 0:
            return False
        stop_index = 0
        for line in util.iter_start_of_line(fh, MAX_LINE_LEN):
            line = line.strip()
            stop_index += 1
            if line == "end_header":
                return True
            items = line.split()
            if items[0] not in valid_header_items:
                return False
            if stop_index > MAX_HEADER_LINES:
                # If this is a PLY file, there must be an unusually
                # large number of comments.
                break
        return False

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        if dataset.has_data():
            with open(dataset.get_file_name(), errors="ignore") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith("format"):
                        items = line.split()
                        dataset.metadata.file_format = items[1]
                    elif line == "end_header":
                        # Metadata is complete.
                        break
                    elif line.startswith("element"):
                        items = line.split()
                        if items[1] == "face":
                            dataset.metadata.face = int(items[2])
                        elif items[1] == "vertex":
                            dataset.metadata.vertex = int(items[2])
                        else:
                            element_tuple = (items[1], int(items[2]))
                            dataset.metadata.other_elements.append(element_tuple)

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek(dataset.get_file_name())
            dataset.blurb = f"Faces: {str(dataset.metadata.face)}, Vertices: {str(dataset.metadata.vertex)}"
        else:
            dataset.peek = "File does not exist"
            dataset.blurb = "File purged from disc"

    def display_peek(self, dataset: DatasetProtocol) -> str:
        try:
            return dataset.peek
        except Exception:
            return f"Ply file ({nice_size(dataset.get_size())})"


class PlyAscii(Ply, data.Text):
    """
    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('test.plyascii')
    >>> PlyAscii().sniff(fname)
    True
    >>> fname = get_test_fname('test.vtkascii')
    >>> PlyAscii().sniff(fname)
    False
    """

    file_ext = "plyascii"
    subtype = "ascii"

    def __init__(self, **kwd):
        data.Text.__init__(self, **kwd)


class PlyBinary(Ply, Binary):
    file_ext = "plybinary"
    subtype = "binary"

    def __init__(self, **kwd):
        Binary.__init__(self, **kwd)


@build_sniff_from_prefix
class Vtk:
    r"""
    The Visualization Toolkit provides a number of source and writer objects to
    read and write popular data file formats. The Visualization Toolkit also
    provides some of its own file formats.

    There are two different styles of file formats available in VTK. The simplest
    are the legacy, serial formats that are easy to read and write either by hand
    or programmatically. However, these formats are less flexible than the XML
    based file formats which support random access, parallel I/O, and portable
    data compression and are preferred to the serial VTK file formats whenever
    possible.

    All keyword phrases are written in ASCII form whether the file is binary or
    ASCII. The binary section of the file (if in binary form) is the data proper;
    i.e., the numbers that define points coordinates, scalars, cell indices, and
    so forth.

    Binary data must be placed into the file immediately after the newline
    ('\\n') character from the previous ASCII keyword and parameter sequence.
    """

    subtype = ""
    # Add metadata elements.
    MetadataElement(name="vtk_version", default=None, desc="Vtk version", readonly=True, optional=True, visible=True)
    MetadataElement(name="file_format", default=None, desc="File format", readonly=True, optional=True, visible=True)
    MetadataElement(name="dataset_type", default=None, desc="Dataset type", readonly=True, optional=True, visible=True)

    # STRUCTURED_GRID data_type.
    MetadataElement(
        name="dimensions", default=[], desc="Dimensions", readonly=True, optional=True, visible=True, no_value=[]
    )
    MetadataElement(name="origin", default=[], desc="Origin", readonly=True, optional=True, visible=True, no_value=[])
    MetadataElement(name="spacing", default=[], desc="Spacing", readonly=True, optional=True, visible=True, no_value=[])

    # POLYDATA data_type (Points element is also a component of UNSTRUCTURED_GRID..
    MetadataElement(name="points", default=None, desc="Points", readonly=True, optional=True, visible=True)
    MetadataElement(name="vertices", default=None, desc="Vertices", readonly=True, optional=True, visible=True)
    MetadataElement(name="lines", default=None, desc="Lines", readonly=True, optional=True, visible=True)
    MetadataElement(name="polygons", default=None, desc="Polygons", readonly=True, optional=True, visible=True)
    MetadataElement(
        name="triangle_strips", default=None, desc="Triangle strips", readonly=True, optional=True, visible=True
    )

    # UNSTRUCTURED_GRID data_type.
    MetadataElement(name="cells", default=None, desc="Cells", readonly=True, optional=True, visible=True)

    # Additional elements not categorized by data_type.
    MetadataElement(
        name="field_names", default=[], desc="Field names", readonly=True, optional=True, visible=True, no_value=[]
    )
    # The keys in the field_components map to the list of field_names in the above element
    # which ensures order for select list options that are built from it.
    MetadataElement(
        name="field_components",
        default={},
        desc="Field names and components",
        readonly=True,
        optional=True,
        visible=True,
        no_value={},
    )

    @abc.abstractmethod
    def __init__(self, **kwd):
        raise NotImplementedError

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        VTK files can be either ASCII or binary, with two different
        styles of file formats: legacy or XML.  We'll assume if the
        file contains a valid VTK header, then it is a valid VTK file.
        """
        if self._is_vtk_header(file_prefix.text_io(errors="ignore"), self.subtype):
            return True
        return False

    def _is_vtk_header(self, fh: "TextIOBase", subtype: str) -> bool:
        """
        The Header section consists of at least 4, but possibly
        5 lines.  This is tricky because sometimes the 4th line
        is blank (in which case the 5th line consists of the
        data_kind) or the 4th line consists of the data_kind (in
        which case the 5th line is blank).
        """
        data_kinds = ["STRUCTURED_GRID", "POLYDATA", "UNSTRUCTURED_GRID", "STRUCTURED_POINTS", "RECTILINEAR_GRID"]

        def check_data_kind(line):
            for data_kind in data_kinds:
                if line.find(data_kind) >= 0:
                    return True
            return False

        # Line 1: vtk DataFile Version 3.0
        line = get_next_line(fh)
        if line.find("vtk") < 0:
            return False
        # Line 2: can be anything - skip it
        line = get_next_line(fh)
        # Line 3: ASCII or BINARY
        line = get_next_line(fh)
        if line.find(subtype) < 0:
            return False
        # Line 4:
        line = get_next_line(fh)
        if line:
            return check_data_kind(line)
        # line 5:
        line = get_next_line(fh)
        if line:
            return check_data_kind(line)
        return False

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        if dataset.has_data():
            dataset.metadata.field_names = []
            dataset.metadata.field_components = {}
            dataset_type = None
            field_components = {}
            dataset_structure_complete = False
            processing_field_section = False
            with open(dataset.get_file_name(), errors="ignore") as fh:
                for i, line in enumerate(fh):
                    line = line.strip()
                    if not line:
                        continue
                    if i < 3:
                        dataset = self.set_initial_metadata(i, line, dataset)
                    elif dataset.metadata.file_format == "ASCII" or not util.is_binary(line):
                        if dataset_structure_complete:
                            """
                            The final part of legacy VTK files describes the dataset attributes.
                            This part begins with the keywords POINT_DATA or CELL_DATA, followed
                            by an integer number specifying the number of points or cells,
                            respectively. Other keyword/data combinations then define the actual
                            dataset attribute values (i.e., scalars, vectors, tensors, normals,
                            texture coordinates, or field data).  Dataset attributes are supported
                            for both points and cells.

                            Each type of attribute data has a dataName associated with it. This is
                            a character string (without embedded whitespace) used to identify a
                            particular data.  The dataName is used by the VTK readers to extract
                            data. As a result, more than one attribute data of the same type can be
                            included in a file.  For example, two different scalar fields defined
                            on the dataset points, pressure and temperature, can be contained in
                            the same file.  If the appropriate dataName is not specified in the VTK
                            reader, then the first data of that type is extracted from the file.
                            """
                            items = line.split()
                            if items[0] == "SCALARS":
                                # Example: SCALARS surface_field double 3
                                # Scalar definition includes specification of a lookup table. The
                                # definition of a lookup table is optional. If not specified, the
                                # default VTK table will be used, and tableName should be
                                # "default". Also note that the numComp variable is optional.  By
                                # default the number of components is equal to one.  The parameter
                                # numComp must range between (1,4) inclusive; in versions of VTK
                                # prior to vtk2.3 this parameter was not supported.
                                field_name = items[1]
                                dataset.metadata.field_names.append(field_name)
                                try:
                                    num_components = int(items[-1])
                                except Exception:
                                    num_components = 1
                                field_component_indexes = [str(i) for i in range(num_components)]
                                field_components[field_name] = field_component_indexes
                            elif items[0] == "FIELD":
                                # The dataset consists of CELL_DATA.
                                # FIELD FieldData 2
                                processing_field_section = True
                                num_fields = int(items[-1])
                                fields_processed: List[str] = []
                            elif processing_field_section:
                                if len(fields_processed) == num_fields:
                                    processing_field_section = False
                                else:
                                    try:
                                        float(items[0])
                                        # Don't process the cell data.
                                        # 0.0123457 0.197531
                                    except Exception:
                                        # Line consists of arrayName numComponents numTuples dataType.
                                        # Example: surface_field1 1 12 double
                                        field_name = items[0]
                                        dataset.metadata.field_names.append(field_name)
                                        num_components = int(items[1])
                                        field_component_indexes = [str(i) for i in range(num_components)]
                                        field_components[field_name] = field_component_indexes
                                        fields_processed.append(field_name)
                        elif line.startswith("CELL_DATA"):
                            # CELL_DATA 3188
                            dataset_structure_complete = True
                            dataset.metadata.cells = int(line.split()[1])
                        elif line.startswith("POINT_DATA"):
                            # POINT_DATA 1876
                            dataset_structure_complete = True
                            dataset.metadata.points = int(line.split()[1])
                        else:
                            dataset, dataset_type = self.set_structure_metadata(line, dataset, dataset_type)
            if len(field_components) > 0:
                dataset.metadata.field_components = field_components

    def set_initial_metadata(self, i: int, line: str, dataset: DatasetProtocol) -> DatasetProtocol:
        if i == 0:
            # The first part of legacy VTK files is the file version and
            # identifier. This part contains the single line:
            # # vtk DataFile Version X.Y
            dataset.metadata.vtk_version = line.lower().split("version")[1]
            # The second part of legacy VTK files is the header. The header
            # consists of a character string terminated by end-of-line
            # character \n. The header is 256 characters maximum. The header
            # can be used to describe the data and include any other pertinent
            # information.  We skip the header line...
        elif i == 2:
            # The third part of legacy VTK files is the file format.  The file
            # format describes the type of file, either ASCII or binary. On
            # this line the single word ASCII or BINARY must appear.
            dataset.metadata.file_format = line
        return dataset

    def set_structure_metadata(
        self, line: str, dataset: DatasetProtocol, dataset_type: Optional[str]
    ) -> Tuple[DatasetProtocol, Optional[str]]:
        """
        The fourth part of legacy VTK files is the dataset structure. The
        geometry part describes the geometry and topology of the dataset.
        This part begins with a line containing the keyword DATASET followed
        by a keyword describing the type of dataset.  Then, depending upon
        the type of dataset, other keyword/ data combinations define the
        actual data.
        """
        if dataset_type is None and line.startswith("DATASET"):
            dataset_type = line.split()[1]
            dataset.metadata.dataset_type = dataset_type
        if dataset_type == "STRUCTURED_GRID":
            # The STRUCTURED_GRID format supports 1D, 2D, and 3D structured
            # grid datasets.  The dimensions nx, ny, nz must be greater
            # than or equal to 1.  The point coordinates are defined by the
            # data in the POINTS section. This consists of x-y-z data values
            # for each point.
            if line.startswith("DIMENSIONS"):
                # DIMENSIONS 10 5 1
                dataset.metadata.dimensions = [line.split()[1:]]
            elif line.startswith("ORIGIN"):
                # ORIGIN 0 0 0
                dataset.metadata.origin = [line.split()[1:]]
            elif line.startswith("SPACING"):
                # SPACING 1 1 1
                dataset.metadata.spacing = [line.split()[1:]]
        elif dataset_type == "POLYDATA":
            # The polygonal dataset consists of arbitrary combinations
            # of surface graphics primitives vertices, lines, polygons
            # and triangle strips.  Polygonal data is defined by the POINTS,
            # VERTICES, LINES, POLYGONS, or TRIANGLE_STRIPS sections.
            if line.startswith("POINTS"):
                # POINTS 18 float
                dataset.metadata.points = int(line.split()[1])
            elif line.startswith("VERTICES"):
                dataset.metadata.vertices = int(line.split()[1])
            elif line.startswith("LINES"):
                # LINES 5 17
                dataset.metadata.lines = int(line.split()[1])
            elif line.startswith("POLYGONS"):
                # POLYGONS 6 30
                dataset.metadata.polygons = int(line.split()[1])
            elif line.startswith("TRIANGLE_STRIPS"):
                # TRIANGLE_STRIPS 2212 16158
                dataset.metadata.triangle_strips = int(line.split()[1])
        elif dataset_type == "UNSTRUCTURED_GRID":
            # The unstructured grid dataset consists of arbitrary combinations
            # of any possible cell type. Unstructured grids are defined by points,
            # cells, and cell types.
            if line.startswith("POINTS"):
                # POINTS 18 float
                dataset.metadata.points = int(line.split()[1])
            if line.startswith("CELLS"):
                # CELLS 756 3024
                dataset.metadata.cells = int(line.split()[1])
        return dataset, dataset_type

    def get_blurb(self, dataset: HasMetadata) -> str:
        blurb = ""
        if dataset.metadata.vtk_version is not None:
            blurb += f"VTK Version {str(dataset.metadata.vtk_version)}"
        if dataset.metadata.dataset_type is not None:
            if blurb:
                blurb += " "
            blurb += str(dataset.metadata.dataset_type)
        return blurb or "VTK data"

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek(dataset.get_file_name())
            dataset.blurb = self.get_blurb(dataset)
        else:
            dataset.peek = "File does not exist"
            dataset.blurb = "File purged from disc"

    def display_peek(self, dataset: DatasetProtocol) -> str:
        try:
            return dataset.peek
        except Exception:
            return f"Vtk file ({nice_size(dataset.get_size())})"


class VtkAscii(Vtk, data.Text):
    """
    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('test.vtkascii')
    >>> VtkAscii().sniff(fname)
    True
    >>> fname = get_test_fname('test.vtkbinary')
    >>> VtkAscii().sniff(fname)
    False
    """

    file_ext = "vtkascii"
    subtype = "ASCII"

    def __init__(self, **kwd):
        data.Text.__init__(self, **kwd)


class VtkBinary(Vtk, Binary):
    """
    >>> from galaxy.datatypes.sniff import get_test_fname
    >>> fname = get_test_fname('test.vtkbinary')
    >>> VtkBinary().sniff(fname)
    True
    >>> fname = get_test_fname('test.vtkascii')
    >>> VtkBinary().sniff(fname)
    False
    """

    file_ext = "vtkbinary"
    subtype = "BINARY"

    def __init__(self, **kwd):
        Binary.__init__(self, **kwd)


class STL(data.Data):
    file_ext = "stl"


@build_sniff_from_prefix
class NeperTess(data.Text):
    """
    Neper Tessellation File

    Example::

        ***tess
        **format
            format
        **general
            dim type
        **cell
            number_of_cells
    """

    file_ext = "neper.tess"
    MetadataElement(name="format", default=None, desc="format", readonly=True, visible=True)
    MetadataElement(name="dimension", default=None, desc="dimension", readonly=True, visible=True)
    MetadataElement(name="cells", default=None, desc="cells", readonly=True, visible=True)

    def __init__(self, **kwd):
        data.Text.__init__(self, **kwd)

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Neper tess format, starts with ``***tess``

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('test.neper.tess')
        >>> NeperTess().sniff(fname)
        True
        >>> fname = get_test_fname('test.neper.tesr')
        >>> NeperTess().sniff(fname)
        False
        """
        return file_prefix.text_io(errors="ignore").readline(10).startswith("***tess")

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        if dataset.has_data():
            with open(dataset.get_file_name(), errors="ignore") as fh:
                for i, line in enumerate(fh):
                    line = line.strip()
                    if not line or i > 6:
                        break
                    if i == 0 and not line.startswith("***tess"):
                        break
                    if i == 2:
                        dataset.metadata.format = line
                    if i == 4:
                        dataset.metadata.dimension = int(line.split()[0])
                    if i == 6:
                        dataset.metadata.cells = int(line)

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek(dataset.get_file_name(), line_count=7)
            dataset.blurb = f"format: {str(dataset.metadata.format)} dim: {str(dataset.metadata.dimension)} cells: {str(dataset.metadata.cells)}"
        else:
            dataset.peek = "File does not exist"
            dataset.blurb = "File purged from disc"


@build_sniff_from_prefix
class NeperTesr(Binary):
    """
    Neper Raster Tessellation File

    Example::

        ***tesr
        **format
            format
        **general
            dimension
            size_x size_y [size_z]
            voxsize_x voxsize_y [voxsize_z]
        [*origin
            origin_x origin_y [origin_z]]
        [*hasvoid has_void]
        [**cell
            number_of_cells
    """

    file_ext = "neper.tesr"
    MetadataElement(name="format", default=None, desc="format", readonly=True, visible=True)
    MetadataElement(name="dimension", default=None, desc="dimension", readonly=True, visible=True)
    MetadataElement(name="size", default=[], desc="size", readonly=True, visible=True)
    MetadataElement(name="voxsize", default=[], desc="voxsize", readonly=True, visible=True)
    MetadataElement(name="origin", default=[], desc="origin", readonly=True, visible=True)
    MetadataElement(name="cells", default=None, desc="cells", readonly=True, visible=True)

    def __init__(self, **kwd):
        Binary.__init__(self, **kwd)

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Neper tesr format, starts with ``***tesr``

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('test.neper.tesr')
        >>> NeperTesr().sniff(fname)
        True
        >>> fname = get_test_fname('test.neper.tess')
        >>> NeperTesr().sniff(fname)
        False
        """
        return file_prefix.text_io(errors="ignore").readline(10).startswith("***tesr")

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        if dataset.has_data():
            with open(dataset.get_file_name(), errors="ignore") as fh:
                field = ""
                for i, line in enumerate(fh):
                    line = line.strip()
                    if not line or i > 12:
                        break
                    if i == 0 and not line.startswith("***tesr"):
                        break
                    if line.startswith("*"):
                        field = line
                        continue
                    if i == 2:
                        dataset.metadata.format = line.split()[0]
                        continue
                    if i == 4:
                        dataset.metadata.dimension = line.split()[0]
                        continue
                    if i == 5:
                        dataset.metadata.size = line.split()
                        continue
                    if i == 6:
                        dataset.metadata.voxsize = line.split()
                        continue
                    if field.startswith("*origin"):
                        dataset.metadata.origin = line.split()
                        continue
                    if field.startswith("**cell"):
                        dataset.metadata.cells = int(line)
                        break

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek(dataset.get_file_name(), line_count=9)
            dataset.blurb = f"format: {str(dataset.metadata.format)} dim: {str(dataset.metadata.dimension)} cells: {str(dataset.metadata.cells)}"
        else:
            dataset.peek = "File does not exist"
            dataset.blurb = "File purged from disc"


class NeperPoints(data.Text):
    """
    Neper Position File
    Neper position format has 1 - 3 floats per line separated by white space.
    """

    file_ext = "neper.points"
    MetadataElement(name="dimension", default=None, desc="dimension", readonly=True, visible=True)

    def __init__(self, **kwd):
        data.Text.__init__(self, **kwd)

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        data.Text.set_meta(self, dataset, overwrite=overwrite, **kwd)
        if dataset.has_data():
            with open(dataset.get_file_name(), errors="ignore") as fh:
                dataset.metadata.dimension = self._get_dimension(fh)

    def _get_dimension(self, fh: "TextIOBase", maxlines: int = 100, sep: Optional[str] = None) -> Optional[float]:
        dim = None
        try:
            for i, line in enumerate(fh):
                if not line:
                    break
                pts = len([float(x) for x in line.strip().split(sep=sep)])
                if dim is not None and pts != dim:
                    return None
                elif 1 <= pts <= 3:
                    dim = pts
                else:
                    return None
                if i > maxlines:
                    break
        except Exception:
            return None
        return dim

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        data.Text.set_peek(self, dataset)
        if not dataset.dataset.purged:
            dataset.blurb += f" dim: {str(dataset.metadata.dimension)}"


class NeperPointsTabular(NeperPoints, Tabular):
    """
    Neper Position File
    Neper position format has 1 - 3 floats per line separated by TABs.
    """

    file_ext = "neper.points.tsv"

    def __init__(self, **kwd):
        Tabular.__init__(self, **kwd)

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        Tabular.set_meta(self, dataset, overwrite=overwrite, **kwd)
        if dataset.has_data():
            with open(dataset.get_file_name(), errors="ignore") as fh:
                dataset.metadata.dimension = self._get_dimension(fh)

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        Tabular.set_peek(self, dataset)
        if not dataset.dataset.purged:
            dataset.blurb += f" dim: {str(dataset.metadata.dimension)}"


class NeperMultiScaleCell(data.Text):
    """
    Neper Multiscale Cell File
    """

    file_ext = "neper.mscell"


@build_sniff_from_prefix
class GmshMsh(Binary):
    """Gmsh Mesh File"""

    file_ext = "gmsh.msh"
    is_binary = "maybe"
    MetadataElement(name="version", default=None, desc="version", readonly=True, visible=True)
    MetadataElement(name="format", default=None, desc="format", readonly=True, visible=True)

    def __init__(self, **kwd):
        Binary.__init__(self, **kwd)

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Gmsh msh format, starts with ``$MeshFormat``

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('test.gmsh.msh')
        >>> GmshMsh().sniff(fname)
        True
        >>> fname = get_test_fname('test.neper.tesr')
        >>> GmshMsh().sniff(fname)
        False
        """
        return file_prefix.text_io(errors="ignore").readline().startswith("$MeshFormat")

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        if dataset.has_data():
            with open(dataset.get_file_name(), errors="ignore") as fh:
                for i, line in enumerate(fh):
                    line = line.strip()
                    if not line or i > 1:
                        break
                    if i == 0 and not line.startswith("$MeshFormat"):
                        break
                    if i == 1:
                        fields = line.split()
                        if len(fields) > 0:
                            dataset.metadata.version = fields[0]
                        if len(fields) > 1:
                            dataset.metadata.format = "ASCII" if fields[1] == "0" else "binary"

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek(dataset.get_file_name(), line_count=3)
            dataset.blurb = f"Gmsh verion: {str(dataset.metadata.version)} {str(dataset.metadata.format)}"
        else:
            dataset.peek = "File does not exist"
            dataset.blurb = "File purged from disc"


class GmshGeo(data.Text):
    """Gmsh geometry File"""

    file_ext = "gmsh.geo"


class ZsetGeof(data.Text):
    """
    Z-set geof File
    """

    file_ext = "zset.geof"


# Utility functions
def get_next_line(fh):
    line = fh.readline(MAX_LINE_LEN)
    if not line.endswith("\n"):
        # Discard the rest of the line
        fh.readline()
    return line.strip()

class VtkXml(GenericXml):
    """Format for defining VTK (XML based) and its sub-datatypes. https://docs.vtk.org/en/latest/design_documents/VTKFileFormats.html"""

    edam_data = "edam:data_3671"
    edam_format = "edam:format_3621"
    file_ext = "vtkxml"

    MetadataElement(name="vtk_version", default=None, desc="Vtk version", readonly=True, optional=True, visible=True)
    MetadataElement(name="file_format", default=None, desc="File format", readonly=True, optional=True, visible=True)
    MetadataElement(name="dataset_type", default=None, desc="Dataset type", readonly=True, optional=True, visible=True)

    def set_meta(self, dataset: DatasetProtocol, **kwd) -> None:
        """
        Sets metadata for the VTK dataset, including VTK version, file format, and dataset type.
        """
        file_path = dataset.file_name
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            vtk_version = root.attrib.get("version", "unknown")  
            file_format = root.attrib.get("type", "unknown")   
            dataset_type = root.tag                              
            self.vtk_version = vtk_version
            self.file_format = file_format
            self.dataset_type = dataset_type

        except ET.ParseError:
            self.vtk_version = "unknown"
            self.file_format = "unknown"
            self.dataset_type = "unknown"

            
    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        """Set the peek and blurb text"""
        if not dataset.dataset.purged:
            dataset.peek = data.get_file_peek(dataset.get_file_name())
            "VTK Unstructured Grid file (VTU)"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """ "Checking for keystring - 'VTKFile type="UnstructuredGrid"'.

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname( 'data.vtu' )
        >>> Vtu().sniff( fname )
        True
        >>> fname = get_test_fname( 'solid.xml' )
        >>> Vtu().sniff( fname )
        False
        """
        return self._has_root_element_in_prefix(file_prefix, 'VTKFile type="UnstructuredGrid"')
