import logging
import os
import re
from typing import (
    Callable,
    Dict,
    List,
)

from galaxy.datatypes import metadata
from galaxy.datatypes.binary import Binary
from galaxy.datatypes.data import (
    get_file_peek,
    Text,
)
from galaxy.datatypes.metadata import MetadataElement
from galaxy.datatypes.protocols import DatasetProtocol
from galaxy.datatypes.sniff import (
    build_sniff_from_prefix,
    FilePrefix,
    get_headers,
    iter_headers,
)
from galaxy.datatypes.tabular import Tabular
from galaxy.datatypes.util.generic_util import count_special_lines
from galaxy.datatypes.xml import GenericXml
from galaxy.util import (
    commands,
    unicodify,
)

# optional import to enhance metadata
try:
    from ase import io as ase_io
except ImportError:
    ase_io = None

log = logging.getLogger(__name__)


def count_lines(filename, non_empty=False):
    """
    counting the number of lines from the 'filename' file
    """
    if non_empty:
        cmd = ["grep", "-cve", r"^\s*$", filename]
    else:
        cmd = ["wc", "-l", filename]
    try:
        out = commands.execute(cmd)
    except commands.CommandLineException as e:
        log.error(unicodify(e))
        return 0
    return int(out.split()[0])


class GenericMolFile(Text):
    """
    Abstract class for most of the molecule files.
    """

    MetadataElement(
        name="number_of_molecules",
        default=0,
        desc="Number of molecules",
        readonly=True,
        visible=True,
        optional=True,
        no_value=0,
    )

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            if dataset.metadata.number_of_molecules == 1:
                dataset.blurb = "1 molecule"
            else:
                dataset.blurb = f"{dataset.metadata.number_of_molecules} molecules"
            dataset.peek = get_file_peek(dataset.file_name)
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def get_mime(self) -> str:
        return "text/plain"

    element_symbols = [
        "Ac",
        "Ag",
        "Al",
        "Am",
        "Ar",
        "As",
        "At",
        "Au",
        "B ",
        "Ba",
        "Be",
        "Bh",
        "Bi",
        "Bk",
        "Br",
        "C ",
        "Ca",
        "Cd",
        "Ce",
        "Cf",
        "Cl",
        "Cm",
        "Co",
        "Cr",
        "Cs",
        "Cu",
        "Ds",
        "Db",
        "Dy",
        "Er",
        "Es",
        "Eu",
        "F ",
        "Fe",
        "Fm",
        "Fr",
        "Ga",
        "Gd",
        "Ge",
        "H ",
        "He",
        "Hf",
        "Hg",
        "Ho",
        "Hs",
        "I ",
        "In",
        "Ir",
        "K ",
        "Kr",
        "La",
        "Li",
        "Lr",
        "Lu",
        "Md",
        "Mg",
        "Mn",
        "Mo",
        "Mt",
        "N ",
        "Na",
        "Nb",
        "Nd",
        "Ne",
        "Ni",
        "No",
        "Np",
        "O ",
        "Os",
        "P ",
        "Pa",
        "Pb",
        "Pd",
        "Pm",
        "Po",
        "Pr",
        "Pt",
        "Pu",
        "Ra",
        "Rb",
        "Re",
        "Rf",
        "Rg",
        "Rh",
        "Rn",
        "Ru",
        "S ",
        "Sb",
        "Sc",
        "Se",
        "Sg",
        "Si",
        "Sm",
        "Sn",
        "Sr",
        "Ta",
        "Tb",
        "Tc",
        "Te",
        "Th",
        "Ti",
        "Tl",
        "Tm",
        "U ",
        "V ",
        "W ",
        "Xe",
        "Y ",
        "Yb",
        "Zn",
        "Zr",
    ]


class MOL(GenericMolFile):
    file_ext = "mol"

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        """
        Set the number molecules, in the case of MOL its always one.
        """
        dataset.metadata.number_of_molecules = 1


@build_sniff_from_prefix
class SDF(GenericMolFile):
    file_ext = "sdf"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Try to guess if the file is a SDF2 file.

        An SDfile (structure-data file) can contain multiple compounds.

        Each compound starts with a block in V2000 or V3000 molfile format,
        which ends with a line equal to 'M  END'.
        This is followed by a non-structural data block, which ends with a line
        equal to '$$$$'.

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('drugbank_drugs.sdf')
        >>> SDF().sniff(fname)
        True
        >>> fname = get_test_fname('github88.v3k.sdf')
        >>> SDF().sniff(fname)
        True
        >>> fname = get_test_fname('chebi_57262.v3k.mol')
        >>> SDF().sniff(fname)
        False
        """
        m_end_found = False
        limit = 10000
        idx = 0
        for line in file_prefix.line_iterator():
            idx += 1
            line = line.rstrip("\n\r")
            if idx < 4:
                continue
            elif idx == 4:
                if len(line) != 39 or not (line.endswith(" V2000") or line.endswith(" V3000")):
                    return False
            elif not m_end_found:
                if line == "M  END":
                    m_end_found = True
            elif line == "$$$$":
                return True
            if idx == limit:
                break
        return False

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        """
        Set the number of molecules in dataset.
        """
        dataset.metadata.number_of_molecules = count_special_lines(r"^\$\$\$\$$", dataset.file_name)

    @classmethod
    def split(cls, input_datasets: List, subdir_generator_function: Callable, split_params: Dict) -> None:
        """
        Split the input files by molecule records.
        """
        if split_params is None:
            return None

        if len(input_datasets) > 1:
            raise Exception("SD-file splitting does not support multiple files")
        input_files = [ds.file_name for ds in input_datasets]

        chunk_size = None
        if split_params["split_mode"] == "number_of_parts":
            raise Exception(f"Split mode \"{split_params['split_mode']}\" is currently not implemented for SD-files.")
        elif split_params["split_mode"] == "to_size":
            chunk_size = int(split_params["split_size"])
        else:
            raise Exception(f"Unsupported split mode {split_params['split_mode']}")

        def _read_sdf_records(filename):
            lines = []
            with open(filename) as handle:
                for line in handle:
                    lines.append(line)
                    if line.startswith("$$$$"):
                        yield lines
                        lines = []

        def _write_part_sdf_file(accumulated_lines):
            part_dir = subdir_generator_function()
            part_path = os.path.join(part_dir, os.path.basename(input_files[0]))
            with open(part_path, "w") as part_file:
                part_file.writelines(accumulated_lines)

        try:
            sdf_records = _read_sdf_records(input_files[0])
            sdf_lines_accumulated = []
            for counter, sdf_record in enumerate(sdf_records, start=1):
                sdf_lines_accumulated.extend(sdf_record)
                if counter % chunk_size == 0:
                    _write_part_sdf_file(sdf_lines_accumulated)
                    sdf_lines_accumulated = []
            if sdf_lines_accumulated:
                _write_part_sdf_file(sdf_lines_accumulated)
        except Exception as e:
            log.error("Unable to split files: %s", unicodify(e))
            raise


@build_sniff_from_prefix
class MOL2(GenericMolFile):
    file_ext = "mol2"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Try to guess if the file is a MOL2 file.

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('drugbank_drugs.mol2')
        >>> MOL2().sniff(fname)
        True
        >>> fname = get_test_fname('drugbank_drugs.cml')
        >>> MOL2().sniff(fname)
        False
        """
        limit = 60
        idx = 0
        for line in file_prefix.line_iterator():
            line = line.rstrip("\n\r")
            if line == "@<TRIPOS>MOLECULE":
                return True
            idx += 1
            if idx == limit:
                break
        return False

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        """
        Set the number of lines of data in dataset.
        """
        dataset.metadata.number_of_molecules = count_special_lines("@<TRIPOS>MOLECULE", dataset.file_name)

    @classmethod
    def split(cls, input_datasets: List, subdir_generator_function: Callable, split_params: Dict) -> None:
        """
        Split the input files by molecule records.
        """
        if split_params is None:
            return None

        if len(input_datasets) > 1:
            raise Exception("MOL2-file splitting does not support multiple files")
        input_files = [ds.file_name for ds in input_datasets]

        chunk_size = None
        if split_params["split_mode"] == "number_of_parts":
            raise Exception(f"Split mode \"{split_params['split_mode']}\" is currently not implemented for MOL2-files.")
        elif split_params["split_mode"] == "to_size":
            chunk_size = int(split_params["split_size"])
        else:
            raise Exception(f"Unsupported split mode {split_params['split_mode']}")

        def _read_mol2_records(filename):
            lines = []
            start = True
            with open(filename) as handle:
                for line in handle:
                    if line.startswith("@<TRIPOS>MOLECULE"):
                        if start:
                            start = False
                        else:
                            yield lines
                            lines = []
                    lines.append(line)

        def _write_part_mol2_file(accumulated_lines):
            part_dir = subdir_generator_function()
            part_path = os.path.join(part_dir, os.path.basename(input_files[0]))
            with open(part_path, "w") as part_file:
                part_file.writelines(accumulated_lines)

        try:
            mol2_records = _read_mol2_records(input_files[0])
            mol2_lines_accumulated = []
            for counter, mol2_record in enumerate(mol2_records, start=1):
                mol2_lines_accumulated.extend(mol2_record)
                if counter % chunk_size == 0:
                    _write_part_mol2_file(mol2_lines_accumulated)
                    mol2_lines_accumulated = []
            if mol2_lines_accumulated:
                _write_part_mol2_file(mol2_lines_accumulated)
        except Exception as e:
            log.error("Unable to split files: %s", unicodify(e))
            raise


@build_sniff_from_prefix
class FPS(GenericMolFile):
    """
    chemfp fingerprint file: http://code.google.com/p/chem-fingerprints/wiki/FPS
    """

    file_ext = "fps"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Try to guess if the file is a FPS file.

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('q.fps')
        >>> FPS().sniff(fname)
        True
        >>> fname = get_test_fname('drugbank_drugs.cml')
        >>> FPS().sniff(fname)
        False
        """
        header = get_headers(file_prefix, sep="\t", count=1)
        if header[0][0].strip() == "#FPS1":
            return True
        else:
            return False

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        """
        Set the number of lines of data in dataset.
        """
        dataset.metadata.number_of_molecules = count_special_lines("^#", dataset.file_name, invert=True)

    @classmethod
    def split(cls, input_datasets: List, subdir_generator_function: Callable, split_params: Dict) -> None:
        """
        Split the input files by fingerprint records.
        """
        if split_params is None:
            return None

        if len(input_datasets) > 1:
            raise Exception("FPS-file splitting does not support multiple files")
        input_files = [ds.file_name for ds in input_datasets]

        chunk_size = None
        if split_params["split_mode"] == "number_of_parts":
            raise Exception(f"Split mode \"{split_params['split_mode']}\" is currently not implemented for MOL2-files.")
        elif split_params["split_mode"] == "to_size":
            chunk_size = int(split_params["split_size"])
        else:
            raise Exception(f"Unsupported split mode {split_params['split_mode']}")

        def _write_part_fingerprint_file(accumulated_lines):
            part_dir = subdir_generator_function()
            part_path = os.path.join(part_dir, os.path.basename(input_files[0]))
            with open(part_path, "w") as part_file:
                part_file.writelines(accumulated_lines)

        try:
            header_lines = []
            lines_accumulated = []
            fingerprint_counter = 0
            for line in open(input_files[0]):
                if not line.strip():
                    continue
                if line.startswith("#"):
                    header_lines.append(line)
                else:
                    fingerprint_counter += 1
                    lines_accumulated.append(line)
                if fingerprint_counter != 0 and fingerprint_counter % chunk_size == 0:
                    _write_part_fingerprint_file(header_lines + lines_accumulated)
                    lines_accumulated = []
            if lines_accumulated:
                _write_part_fingerprint_file(header_lines + lines_accumulated)
        except Exception as e:
            log.error("Unable to split files: %s", unicodify(e))
            raise

    @staticmethod
    def merge(split_files: List[str], output_file: str) -> None:
        """
        Merging fps files requires merging the header manually.
        We take the header from the first file.
        """
        if len(split_files) == 1:
            # For one file only, use base class method (move/copy)
            return Text.merge(split_files, output_file)
        if not split_files:
            raise ValueError(f"No fps files given, {split_files!r}, to merge into {output_file}")
        with open(output_file, "w") as out:
            first = True
            for filename in split_files:
                with open(filename) as handle:
                    for line in handle:
                        if line.startswith("#"):
                            if first:
                                out.write(line)
                        else:
                            # line is no header and not a comment, we assume the first header is written to out and we set 'first' to False
                            first = False
                            out.write(line)


class OBFS(Binary):
    """OpenBabel Fastsearch format (fs)."""

    file_ext = "obfs"
    composite_type = "basic"

    MetadataElement(
        name="base_name",
        default="OpenBabel Fastsearch Index",
        readonly=True,
        visible=True,
        optional=True,
    )

    def __init__(self, **kwd):
        """
        A Fastsearch Index consists of a binary file with the fingerprints
        and a pointer the actual molecule file.
        """
        super().__init__(**kwd)
        self.add_composite_file("molecule.fs", is_binary=True, description="OpenBabel Fastsearch Index")
        self.add_composite_file("molecule.sdf", optional=True, is_binary=False, description="Molecule File")
        self.add_composite_file("molecule.smi", optional=True, is_binary=False, description="Molecule File")
        self.add_composite_file("molecule.inchi", optional=True, is_binary=False, description="Molecule File")
        self.add_composite_file("molecule.mol2", optional=True, is_binary=False, description="Molecule File")
        self.add_composite_file("molecule.cml", optional=True, is_binary=False, description="Molecule File")

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        """Set the peek and blurb text."""
        if not dataset.dataset.purged:
            dataset.peek = "OpenBabel Fastsearch Index"
            dataset.blurb = "OpenBabel Fastsearch Index"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset: DatasetProtocol) -> str:
        """Create HTML content, used for displaying peek."""
        try:
            return dataset.peek
        except Exception:
            return "OpenBabel Fastsearch Index"

    def get_mime(self) -> str:
        """Returns the mime type of the datatype (pretend it is text for peek)"""
        return "text/plain"

    @staticmethod
    def merge(split_files: List[str], output_file: str) -> None:
        """Merging Fastsearch indices is not supported."""
        raise NotImplementedError("Merging Fastsearch indices is not supported.")

    @classmethod
    def split(cls, input_datasets: List, subdir_generator_function: Callable, split_params: Dict) -> None:
        """Splitting Fastsearch indices is not supported."""
        if split_params is None:
            return None
        raise NotImplementedError("Splitting Fastsearch indices is not possible.")


class DRF(GenericMolFile):
    file_ext = "drf"

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        """
        Set the number of lines of data in dataset.
        """
        dataset.metadata.number_of_molecules = count_special_lines('"ligand id"', dataset.file_name, invert=True)


class PHAR(GenericMolFile):
    """
    Pharmacophore database format from silicos-it.
    """

    file_ext = "phar"

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek(dataset.file_name)
            dataset.blurb = "pharmacophore"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"


@build_sniff_from_prefix
class PDB(GenericMolFile):
    """
    Protein Databank format.
    http://www.wwpdb.org/documentation/format33/v3.3.html
    """

    file_ext = "pdb"
    MetadataElement(name="chain_ids", default=[], desc="Chain IDs", readonly=False, visible=True)

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Try to guess if the file is a PDB file.

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('5e5z.pdb')
        >>> PDB().sniff(fname)
        True
        >>> fname = get_test_fname('drugbank_drugs.cml')
        >>> PDB().sniff(fname)
        False
        """
        headers = iter_headers(file_prefix, sep=" ", count=300)
        h = t = c = s = k = e = False
        for line in headers:
            section_name = line[0].strip()
            if section_name == "HEADER":
                h = True
            elif section_name == "TITLE":
                t = True
            elif section_name == "COMPND":
                c = True
            elif section_name == "SOURCE":
                s = True
            elif section_name == "KEYWDS":
                k = True
            elif section_name == "EXPDTA":
                e = True

        if h * t * c * s * k * e:
            return True
        else:
            return False

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        """
        Find Chain_IDs for metadata.
        """
        try:
            chain_ids = set()
            with open(dataset.file_name) as fh:
                for line in fh:
                    if line.startswith("ATOM  ") or line.startswith("HETATM"):
                        if line[21] != " ":
                            chain_ids.add(line[21])
            dataset.metadata.chain_ids = list(chain_ids)
        except Exception as e:
            log.error("Error finding chain_ids: %s", unicodify(e))
            raise

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            atom_numbers = count_special_lines("^ATOM", dataset.file_name)
            hetatm_numbers = count_special_lines("^HETATM", dataset.file_name)
            chain_ids = ",".join(dataset.metadata.chain_ids) if len(dataset.metadata.chain_ids) > 0 else "None"
            dataset.peek = get_file_peek(dataset.file_name)
            dataset.blurb = f"{atom_numbers} atoms and {hetatm_numbers} HET-atoms\nchain_ids: {chain_ids}"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"


@build_sniff_from_prefix
class PDBQT(GenericMolFile):
    """
    PDBQT Autodock and Autodock Vina format
    http://autodock.scripps.edu/faqs-help/faq/what-is-the-format-of-a-pdbqt-file
    """

    file_ext = "pdbqt"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Try to guess if the file is a PDBQT file.

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('NuBBE_1_obabel_3D.pdbqt')
        >>> PDBQT().sniff(fname)
        True
        >>> fname = get_test_fname('drugbank_drugs.cml')
        >>> PDBQT().sniff(fname)
        False
        """
        headers = iter_headers(file_prefix, sep=" ", count=300)
        h = t = c = s = k = False
        for line in headers:
            section_name = line[0].strip()
            if section_name == "REMARK":
                h = True
            elif section_name == "ROOT":
                t = True
            elif section_name == "ENDROOT":
                c = True
            elif section_name == "BRANCH":
                s = True
            elif section_name == "TORSDOF":
                k = True

        if h * t * c * s * k:
            return True
        else:
            return False

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            root_numbers = count_special_lines("^ROOT", dataset.file_name)
            branch_numbers = count_special_lines("^BRANCH", dataset.file_name)
            dataset.peek = get_file_peek(dataset.file_name)
            dataset.blurb = f"{root_numbers} roots and {branch_numbers} branches"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"


@build_sniff_from_prefix
class PQR(GenericMolFile):
    """
    Protein Databank format.
    https://apbs-pdb2pqr.readthedocs.io/en/latest/formats/pqr.html
    """

    file_ext = "pqr"
    MetadataElement(name="chain_ids", default=[], desc="Chain IDs", readonly=False, visible=True)

    def get_matcher(self) -> re.Pattern:
        """
        Atom and HETATM line fields are space separated, match group:
          0: Field_name
              A string which specifies the type of PQR entry: ATOM or HETATM.
          1: Atom_number
              An integer which provides the atom index.
          2: Atom_name
              A string which provides the atom name.
          3: Residue_name
              A string which provides the residue name.
          5: Chain_ID   (Optional, group 4 is whole field)
              An optional string which provides the chain ID of the atom.
              Note that chain ID support is a new feature of APBS 0.5.0 and later versions.
          6: Residue_number
              An integer which provides the residue index.
          7: X 8: Y 9: Z
              3 floats which provide the atomic coordinates (in angstroms)
          10: Charge
              A float which provides the atomic charge (in electrons).
          11: Radius
              A float which provides the atomic radius (in angstroms).
        """
        pat = (
            r"(ATOM|HETATM)\s+"
            + r"(\d+)\s+"
            + r"([A-Z0-9]+)\s+"
            + r"([A-Z0-9]+)\s+"
            + r"(([A-Z]?)\s+)?"
            + r"([-+]?\d*\.\d+|\d+)\s+"
            + r"([-+]?\d*\.\d+|\d+)\s+"
            + r"([-+]?\d*\.\d+|\d+)\s+"
            + r"([-+]?\d*\.\d+|\d+)\s+"
            + r"([-+]?\d*\.\d+|\d+)\s+"
        )
        return re.compile(pat)

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Try to guess if the file is a PQR file.
        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('5e5z.pqr')
        >>> PQR().sniff(fname)
        True
        >>> fname = get_test_fname('drugbank_drugs.cml')
        >>> PQR().sniff(fname)
        False
        """
        prog = self.get_matcher()
        headers = iter_headers(file_prefix, sep=None, comment_designator="REMARK   5", count=3000)
        h = a = False
        for line in headers:
            section_name = line[0].strip()
            if section_name == "REMARK":
                h = True
            elif section_name == "ATOM" or section_name == "HETATM":
                if prog.match(" ".join(line)):
                    a = True
                    break
        if h * a:
            return True
        else:
            return False

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        """
        Find Optional Chain_IDs for metadata.
        """
        try:
            prog = self.get_matcher()
            chain_ids = set()
            with open(dataset.file_name) as fh:
                for line in fh:
                    if line.startswith("REMARK"):
                        continue
                    match = prog.match(line.rstrip())
                    if match and match.groups()[5]:
                        chain_ids.add(match.groups()[5])
            dataset.metadata.chain_ids = list(chain_ids)
        except Exception as e:
            log.error("Error finding chain_ids: %s", unicodify(e))
            raise

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            atom_numbers = count_special_lines("^ATOM", dataset.file_name)
            hetatm_numbers = count_special_lines("^HETATM", dataset.file_name)
            chain_ids = ",".join(dataset.metadata.chain_ids) if len(dataset.metadata.chain_ids) > 0 else "None"
            dataset.peek = get_file_peek(dataset.file_name)
            dataset.blurb = f"{atom_numbers} atoms and {hetatm_numbers} HET-atoms\nchain_ids: {chain_ids}"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"


@build_sniff_from_prefix
class Cell(GenericMolFile):
    """
    CASTEP CELL format.
    """

    file_ext = "cell"
    meta_error = False
    MetadataElement(
        name="atom_data",
        default=[],
        desc="Atom symbols and positions",
        readonly=True,
        visible=False,
    )
    MetadataElement(
        name="number_of_atoms",
        desc="Number of atoms",
        readonly=True,
        visible=True,
    )
    MetadataElement(
        name="chemical_formula",
        desc="Chemical formula",
        readonly=True,
        visible=True,
    )
    MetadataElement(
        name="is_periodic",
        desc="Periodic boundary conditions",
        readonly=True,
        visible=True,
    )
    MetadataElement(
        name="lattice_parameters",
        desc="Lattice parameters",
        readonly=True,
        visible=True,
    )

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Try to guess if the file is a CASTEP CELL file.

        A fingerprint for CELL files is the use of %BLOCK and %ENDBLOCK to
        denote data blocks (not case sensitive).

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('Si_uppercase.cell')
        >>> Cell().sniff(fname)
        True
        >>> fname = get_test_fname('Si_lowercase.cell')
        >>> Cell().sniff(fname)
        True
        >>> fname = get_test_fname('Si.cif')
        >>> Cell().sniff(fname)
        False
        """
        start_found = False
        for line in file_prefix.line_iterator():
            if not start_found and line.lower().startswith("%block"):
                start_found = True
            elif start_found and line.lower().startswith("%endblock"):
                return True
        return False

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        """
        Find Atom IDs for metadata.
        """
        self.meta_error = False
        if ase_io is None:
            # Don't have optional dependency, can't set advanced values
            return
        else:
            # enhanced metadata
            try:
                ase_data = ase_io.read(dataset.file_name, format="castep-cell")
            except Exception as e:
                log.warning("%s, set_meta Exception during ASE read: %s", self, unicodify(e))
                self.meta_error = True
                return

            try:
                atom_data = [
                    str(sym) + str(pos) for sym, pos in zip(ase_data.get_chemical_symbols(), ase_data.get_positions())
                ]
                chemical_formula = ase_data.get_chemical_formula()
                pbc = ase_data.get_pbc()
                lattice_parameters = ase_data.get_cell().cellpar()
            except Exception as e:
                log.warning("%s, set_meta Exception during ASE metadata collection: %s", self, unicodify(e))
                self.meta_error = True
                return

            # CELL file can only have one molecule
            dataset.metadata.number_of_molecules = 1
            dataset.metadata.atom_data = atom_data
            dataset.metadata.number_of_atoms = len(dataset.metadata.atom_data)
            dataset.metadata.chemical_formula = chemical_formula
            try:
                dataset.metadata.is_periodic = bool(pbc)
            except ValueError:  # pbc is an array
                dataset.metadata.is_periodic = bool(pbc.any())
            dataset.metadata.lattice_parameters = list(lattice_parameters)

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek(dataset.file_name)
            dataset.info = self.get_dataset_info(dataset.metadata)
            structure_string = "structure" if dataset.metadata.number_of_molecules == 1 else "structures"
            dataset.blurb = f"CASTEP CELL file containing {dataset.metadata.number_of_molecules} {structure_string}"

        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def get_dataset_info(self, metadata):
        if self.meta_error:
            info = "Error finding metadata. The file may be formatted incorrectly."
        elif ase_io:
            # enhanced info
            info_list = []
            info_list.append(f"Chemical formula:\n{metadata.chemical_formula}")
            if metadata.is_periodic:
                info_list.append("Periodic:\nYes")
                info_list.append(
                    f"Lattice parameters in axis-angle format:\n{', '.join([str(round(x, 2)) for x in metadata.lattice_parameters])}"
                )
            else:
                info_list.append("Periodic:\nNo")
            info_list.append(f"Atoms in file:\n{metadata.number_of_atoms}")
            info = "\n--\n".join(info_list)
        else:
            info = """
Metadata is limited as the Atomic Simulation Environment (ASE) is not installed.
You can still use this dataset in tools and workflows.
For full metadata, ask your admin to install the 'ase' Python package."""

        return info


@build_sniff_from_prefix
class CIF(GenericMolFile):
    """
    CIF format.
    """

    file_ext = "cif"
    meta_error = False
    MetadataElement(
        name="data_block_names",
        default=[],
        desc="Names of the data blocks",
        readonly=True,
        visible=True,
    )
    MetadataElement(
        name="atom_data",
        default=[],
        desc="Atom symbols and positions",
        readonly=True,
        visible=False,
    )
    MetadataElement(
        name="number_of_atoms",
        desc="Number of atoms",
        readonly=True,
        visible=True,
    )
    MetadataElement(
        name="chemical_formula",
        desc="Chemical formula",
        readonly=True,
        visible=True,
    )
    MetadataElement(
        name="is_periodic",
        desc="Periodic boundary conditions",
        readonly=True,
        visible=True,
    )
    MetadataElement(
        name="lattice_parameters",
        desc="Lattice parameters",
        readonly=True,
        visible=True,
    )

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Try to guess if the file is a CIF file.

        The CIF format and the Relion STAR format have a shared origin.
        Note therefore that STAR files and the STAR sniffer also use ``data_`` blocks.
        STAR files will not pass the CIF sniffer, but CIF files can pass the STAR sniffer.

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('Si.cif')
        >>> CIF().sniff(fname)
        True
        >>> fname = get_test_fname('Si_lowercase.cell')
        >>> CIF().sniff(fname)
        False
        >>> fname = get_test_fname('1.star')
        >>> CIF().sniff(fname)
        False
        """

        # check for optional CIF version marker '#\#CIF_<version>' at start of file
        if file_prefix.startswith("#\\#CIF_"):
            return True

        # no version marker, search for mandatory CIF keywords
        # first non-comment line must begin with 'data_'
        # and '_atom_site_fract_(x|y|z)' must be specified somewhere in the file
        for line in file_prefix.line_iterator():
            if not line:
                continue
            elif line[0] == "#":  # comment so skip
                continue
            elif line.startswith("data_"):
                return file_prefix.search_str("_atom_site_fract_")
            else:  # line has some other content
                return False
        return False

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        """
        Find Atom IDs for metadata.
        """
        self.meta_error = False
        if ase_io is None:
            # Don't have optional dependency, can't set advanced values
            return
        else:
            # enhanced metadata
            try:
                ase_data = ase_io.read(dataset.file_name, index=":", format="cif")
            except Exception as e:
                log.warning("%s, set_meta Exception during ASE read: %s", self, unicodify(e))
                self.meta_error = True
                return

            atom_data = []
            chemical_formula = []
            is_periodic = []
            lattice_parameters = []
            try:
                for block in ase_data:
                    atom_data.append(
                        [str(sym) + str(pos) for sym, pos in zip(block.get_chemical_symbols(), block.get_positions())]
                    )
                    chemical_formula.append(block.get_chemical_formula())
                    pbc = block.get_pbc()
                    try:
                        p = bool(pbc)
                    except ValueError:  # pbc is an array
                        p = bool(pbc.any())
                    is_periodic.append(p)
                    lattice_parameters.append(list(block.get_cell().cellpar()))
            except Exception as e:
                log.warning("%s, set_meta Exception during ASE metadata collection: %s", self, unicodify(e))
                self.meta_error = True
                return

            dataset.metadata.number_of_molecules = len(ase_data)
            dataset.metadata.atom_data = atom_data
            dataset.metadata.number_of_atoms = [len(atoms) for atoms in dataset.metadata.atom_data]
            dataset.metadata.chemical_formula = chemical_formula
            dataset.metadata.is_periodic = is_periodic
            dataset.metadata.lattice_parameters = list(lattice_parameters)

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek(dataset.file_name)
            dataset.info = self.get_dataset_info(dataset.metadata)
            structure_string = "structure" if dataset.metadata.number_of_molecules == 1 else "structures"
            dataset.blurb = f"CIF file containing {dataset.metadata.number_of_molecules} {structure_string}"

        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def get_dataset_info(self, metadata):
        if self.meta_error:
            info = "Error finding metadata. The file may be formatted incorrectly."
        elif ase_io:
            # enhanced info
            info_list = []
            if metadata.number_of_molecules == 1:
                info_list.append(f"Chemical formula:\n{metadata.chemical_formula[0]}")
                if metadata.is_periodic[0]:
                    info_list.append("Periodic:\nYes")
                    info_list.append(
                        f"Lattice parameters in axis-angle format:\n{', '.join([str(round(x, 2)) for x in metadata.lattice_parameters[0]])}"
                    )
                else:
                    info_list.append("Periodic:\nNo")
                info_list.append(f"Atoms in file:\n{metadata.number_of_atoms[0]}")
            elif metadata.number_of_molecules > 1:
                info_list.append("File contains multiple structures; full metadata will not be displayed.")
                formulae = "\n".join(metadata.chemical_formula)
                info_list.append(f"Chemical formula for each structure in this file:\n{formulae}")
            info = "\n--\n".join(info_list)
        else:
            info = """
Metadata is limited as the Atomic Simulation Environment (ASE) is not installed.
You can still use this dataset in tools and workflows.
For full metadata, ask your admin to install the 'ase' Python package."""

        return info


@build_sniff_from_prefix
class XYZ(GenericMolFile):
    """
    XYZ format.
    """

    file_ext = "xyz"
    meta_error = False
    MetadataElement(
        name="atom_data",
        default=[],
        desc="Atom symbols and positions",
        readonly=True,
        visible=False,
    )
    MetadataElement(
        name="number_of_atoms",
        desc="Number of atoms",
        readonly=True,
        visible=True,
    )
    MetadataElement(
        name="chemical_formula",
        desc="Chemical formula",
        readonly=True,
        visible=True,
    )
    MetadataElement(
        name="is_periodic",
        desc="Periodic boundary conditions",
        readonly=True,
        visible=True,
    )
    MetadataElement(
        name="lattice_parameters",
        desc="Lattice parameters",
        readonly=True,
        visible=True,
    )

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Try to guess if the file is a XYZ file.

        XYZ has no fingerprint phrases, so the whole prefix must be checked
        for the correct structure. If the prefix passes, assume the whole file
        passes.

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('Si.xyz')
        >>> XYZ().sniff(fname)
        True
        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('Si_multi.xyz')
        >>> XYZ().sniff(fname)
        True
        >>> fname = get_test_fname('Si.cif')
        >>> XYZ().sniff(fname)
        False
        >>> fname = get_test_fname('not_a_xyz_file.txt')
        >>> XYZ().sniff(fname)
        False
        """

        try:
            self.read_blocks(list(file_prefix.line_iterator()))
            return True
        except (TypeError, ValueError, IndexError):
            return False

    def read_blocks(self, lines: List) -> List:
        """
        Parses and returns a list of dictionaries representing XYZ structure blocks (aka frames).

        Raises IndexError, TypeError, ValueError
        """
        # remove trailing blank lines
        # blank lines not permitted elsewhere in file except for designated comment lines
        while not lines[-1].strip():
            lines = lines[:-1]

        blocks = []

        while lines:
            n_atoms = None
            comment = None
            atoms = []
            try:
                n_atoms = int(lines.pop(0))
                comment = lines.pop(0)
                for _ in range(n_atoms):
                    atom = lines.pop(0)
                    atom = atom.split()
                    symbol = atom[0].lower().capitalize()
                    if symbol not in self.element_symbols:
                        raise ValueError(f"{atom[0]} is not a valid element symbol")

                    # raises ValueError if not valid XYZ format
                    position = [float(i) for i in atom[1:4]]

                    atoms.append(symbol + str(position))
                blocks.append({"number_of_atoms": n_atoms, "comment": comment, "atom_data": atoms})
            except IndexError as e:
                if "pop from empty list" in str(e) and blocks:
                    # we'll require at least one valid block
                    pass
                else:
                    raise
        return blocks

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        """
        Find Atom IDs for metadata.
        """
        self.meta_error = False
        if ase_io is None:
            # Don't have optional dependency, can't set advanced values
            return
        else:
            # enhanced metadata
            try:
                # ASE recommend always parsing as extended xyz
                ase_data = ase_io.read(dataset.file_name, index=":", format="extxyz")
            except Exception as e:
                log.warning("%s, set_meta Exception during ASE read: %s", self, unicodify(e))
                self.meta_error = True
                return

            atom_data = []
            chemical_formula = []
            is_periodic = []
            lattice_parameters = []
            try:
                for block in ase_data:
                    atom_data.append(
                        [str(sym) + str(pos) for sym, pos in zip(block.get_chemical_symbols(), block.get_positions())]
                    )
                    chemical_formula.append(block.get_chemical_formula())
                    pbc = block.get_pbc()
                    try:
                        p = bool(pbc)
                    except ValueError:  # pbc is an array
                        p = bool(pbc.any())
                    is_periodic.append(p)
                    lattice_parameters.append(list(block.get_cell().cellpar()))
            except Exception as e:
                log.warning("%s, set_meta Exception during ASE metadata collection: %s", self, unicodify(e))
                self.meta_error = True
                return

            dataset.metadata.number_of_molecules = len(ase_data)
            dataset.metadata.atom_data = atom_data
            dataset.metadata.number_of_atoms = [len(atoms) for atoms in dataset.metadata.atom_data]
            dataset.metadata.chemical_formula = chemical_formula
            dataset.metadata.is_periodic = is_periodic
            dataset.metadata.lattice_parameters = list(lattice_parameters)

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek(dataset.file_name)
            dataset.info = self.get_dataset_info(dataset.metadata)
            structure_string = "structure" if dataset.metadata.number_of_molecules == 1 else "structures"
            dataset.blurb = f"XYZ file containing {dataset.metadata.number_of_molecules} {structure_string}"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def get_dataset_info(self, metadata):
        if self.meta_error:
            info = "Error finding metadata. The file may be formatted incorrectly."
        elif ase_io:
            # enhanced info
            info_list = []
            if metadata.number_of_molecules == 1:
                info_list.append(f"Chemical formula:\n{metadata.chemical_formula[0]}")
                if metadata.is_periodic[0]:
                    info_list.append("Periodic:\nYes")
                    info_list.append(
                        f"Lattice parameters in axis-angle format:\n{', '.join([str(round(x, 2)) for x in metadata.lattice_parameters[0]])}"
                    )
                else:
                    info_list.append("Periodic:\nNo")
                info_list.append(f"Atoms in file:\n{metadata.number_of_atoms[0]}")
            elif metadata.number_of_molecules > 1:
                info_list.append("File contains multiple structures; full metadata will not be displayed.")
                formulae = "\n".join(metadata.chemical_formula)
                info_list.append(f"Chemical formula for each structure in this file:\n{formulae}")
            info = "\n--\n".join(info_list)
        else:
            info = """
Metadata is limited as the Atomic Simulation Environment (ASE) is not installed.
You can still use this dataset in tools and workflows.
For full metadata, ask your admin to install the 'ase' Python package."""

        return info


@build_sniff_from_prefix
class ExtendedXYZ(XYZ):
    """
    Extended XYZ format.

    Uses specification from https://github.com/libAtoms/extxyz.
    """

    file_ext = "extxyz"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Try to guess if the file is an Extended XYZ file.

        XYZ files will not pass the ExtendedXYZ sniffer, but ExtendedXYZ files can pass the XYZ sniffer.

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('Si.extxyz')
        >>> ExtendedXYZ().sniff(fname)
        True
        >>> fname = get_test_fname('Si.xyz')
        >>> ExtendedXYZ().sniff(fname)
        False
        """
        line_iterator = file_prefix.line_iterator()
        try:
            # fingerprint is 'Properties="<name>:<type>:<number>:..."'
            # in the second line
            # e.g. Properties="species:S:1:pos:R:3:vel:R:3:select:I:1"
            next(line_iterator)
            comment = next(line_iterator)
            properties = re.search(r"Properties=\"?([a-zA-Z0-9:]+)\"?", comment)  # returns None if no match
            return bool(properties)
        except StopIteration:
            # insufficient lines
            return False

    def read_blocks(self, lines: List) -> List:
        """
        Parses and returns a list of XYZ structure blocks (aka frames).

        Raises IndexError, TypeError, ValueError
        """
        # remove trailing blank lines
        # blank lines not permitted elsewhere in file except for designated comment lines
        while not lines[-1].strip():
            lines = lines[:-1]

        blocks = []

        while lines:
            n_atoms = None
            comment = None
            atoms = []

            n_atoms = int(lines.pop(0))
            comment = lines.pop(0)
            # extract column properties
            # these have the format 'Properties="<name>:<type>:<number>:..."' in the comment line
            # e.g. Properties="species:S:1:pos:R:3:vel:R:3:select:I:1"
            properties_matches = re.search(r"Properties=\"?([a-zA-Z0-9:]+)\"?", comment)
            if properties_matches is None:  # re.search returned None
                raise ValueError(f"Could not find column properties in line: {comment}")
            properties = [s.split(":") for s in re.findall(r"[a-zA-Z]+:[SIRL]:[0-9]+", properties_matches.group(1))]
            total_columns = sum(int(s[2]) for s in properties)

            for _ in range(n_atoms):
                atom_dict = {}
                atom = lines.pop(0)
                atom = atom.split()
                if len(atom) != total_columns:
                    raise ValueError(f"Expected {total_columns} columns but found {len(atom)}: {atom}")
                index = 0
                # parse atom data according to column format specified by the properties
                # this processing will raise errors if the format is incorrect
                for property in properties:
                    to_process = atom[index : index + int(property[2])]
                    property_name = property[0]
                    property_type = property[1]
                    for i in to_process:
                        if property_type == "S":  # string
                            # check that any element symbols are correct, otherwise ignore strings
                            if property_name.lower() == "species":
                                symbol = i.lower().capitalize()
                                if symbol not in self.element_symbols:
                                    raise ValueError(f"{i} is not a valid element symbol")
                                else:
                                    atom_dict[property_name] = symbol
                            else:
                                atom_dict[property_name] = i
                        elif property_type == "L":  # logical
                            if re.match(r"(?:[tT]rue|TRUE|T)\b", i):
                                atom_dict[property_name] = True
                            elif re.match(r"(?:[fF]alse|FALSE|F)\b", i):
                                atom_dict[property_name] = False
                            else:
                                raise ValueError(f"{i} is not a valid logical element.")
                        elif property_type in ["I", "R"]:  # integer, float
                            ii = int(i) if property_type == "I" else float(i)
                            if int(property[2]) > 1:  # more than one column for this property - use array
                                if property_name in atom_dict:
                                    atom_dict[property_name].append(ii)
                                else:
                                    atom_dict[property_name] = [ii]
                            else:
                                atom_dict[property_name] = ii
                        else:
                            raise ValueError(f"Could not recognise property type {property_type}.")
                    index += int(property[2])

                atoms.append(atom_dict)

            blocks.append({"number_of_atoms": n_atoms, "comment": comment, "atom_data": atoms})
        return blocks

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        super().set_peek(dataset)
        dataset.blurb = "Extended " + dataset.blurb


class grd(Text):
    file_ext = "grd"

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek(dataset.file_name)
            dataset.blurb = "grids for docking"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"


class grdtgz(Binary):
    file_ext = "grd.tgz"

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            dataset.peek = "binary data"
            dataset.blurb = "compressed grids for docking"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"


@build_sniff_from_prefix
class InChI(Tabular):
    file_ext = "inchi"
    column_names = ["InChI"]
    MetadataElement(name="columns", default=2, desc="Number of columns", readonly=True, visible=False)
    MetadataElement(
        name="column_types",
        default=["str"],
        param=metadata.ColumnTypesParameter,
        desc="Column types",
        readonly=True,
        visible=False,
    )
    MetadataElement(
        name="number_of_molecules",
        default=0,
        desc="Number of molecules",
        readonly=True,
        visible=True,
        optional=True,
        no_value=0,
    )

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        """
        Set the number of lines of data in dataset.
        """
        dataset.metadata.number_of_molecules = self.count_data_lines(dataset)

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            if dataset.metadata.number_of_molecules == 1:
                dataset.blurb = "1 molecule"
            else:
                dataset.blurb = f"{dataset.metadata.number_of_molecules} molecules"
            dataset.peek = get_file_peek(dataset.file_name)
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Try to guess if the file is a InChI file.

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('drugbank_drugs.inchi')
        >>> InChI().sniff(fname)
        True
        >>> fname = get_test_fname('drugbank_drugs.cml')
        >>> InChI().sniff(fname)
        False
        """
        inchi_lines = iter_headers(file_prefix, sep=" ", count=10)
        found_lines = False
        for inchi in inchi_lines:
            if not inchi[0].startswith("InChI="):
                return False
            found_lines = True
        return found_lines


class SMILES(Tabular):
    # It is hard or impossible to sniff a SMILES File. We can try to import the
    # first SMILES and check if it is a molecule, but currently it is not
    # possible to use external libraries in datatype definition files.
    # Moreover it seems impossible to include OpenBabel as Python library
    # because OpenBabel is GPL licensed.
    file_ext = "smi"
    column_names = ["SMILES", "TITLE"]
    MetadataElement(name="columns", default=2, desc="Number of columns", readonly=True, visible=False)
    MetadataElement(
        name="column_types",
        default=["str", "str"],
        param=metadata.ColumnTypesParameter,
        desc="Column types",
        readonly=True,
        visible=False,
    )
    MetadataElement(
        name="number_of_molecules",
        default=0,
        desc="Number of molecules",
        readonly=True,
        visible=True,
        optional=True,
        no_value=0,
    )

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        """
        Set the number of lines of data in dataset.
        """
        dataset.metadata.number_of_molecules = self.count_data_lines(dataset)

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            if dataset.metadata.number_of_molecules == 1:
                dataset.blurb = "1 molecule"
            else:
                dataset.blurb = f"{dataset.metadata.number_of_molecules} molecules"
            dataset.peek = get_file_peek(dataset.file_name)
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"


@build_sniff_from_prefix
class CML(GenericXml):
    """
    Chemical Markup Language
    http://cml.sourceforge.net/
    """

    file_ext = "cml"
    MetadataElement(
        name="number_of_molecules",
        default=0,
        desc="Number of molecules",
        readonly=True,
        visible=True,
        optional=True,
        no_value=0,
    )

    def set_meta(self, dataset: DatasetProtocol, overwrite: bool = True, **kwd) -> None:
        """
        Set the number of lines of data in dataset.
        """
        dataset.metadata.number_of_molecules = count_special_lines(r"^\s*<molecule", dataset.file_name)

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            if dataset.metadata.number_of_molecules == 1:
                dataset.blurb = "1 molecule"
            else:
                dataset.blurb = f"{dataset.metadata.number_of_molecules} molecules"
            dataset.peek = get_file_peek(dataset.file_name)
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Try to guess if the file is a CML file.

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('interval.interval')
        >>> CML().sniff(fname)
        False
        >>> fname = get_test_fname('drugbank_drugs.cml')
        >>> CML().sniff(fname)
        True
        """
        for expected_string in ['<?xml version="1.0"?>', "http://www.xml-cml.org/schema"]:
            if expected_string not in file_prefix.contents_header:
                return False

        return True

    @classmethod
    def split(cls, input_datasets: List, subdir_generator_function: Callable, split_params: Dict) -> None:
        """
        Split the input files by molecule records.
        """
        if split_params is None:
            return None

        if len(input_datasets) > 1:
            raise Exception("CML-file splitting does not support multiple files")
        input_files = [ds.file_name for ds in input_datasets]

        chunk_size = None
        if split_params["split_mode"] == "number_of_parts":
            raise Exception(f"Split mode \"{split_params['split_mode']}\" is currently not implemented for CML-files.")
        elif split_params["split_mode"] == "to_size":
            chunk_size = int(split_params["split_size"])
        else:
            raise Exception(f"Unsupported split mode {split_params['split_mode']}")

        def _read_cml_records(filename):
            lines = []
            with open(filename) as handle:
                for line in handle:
                    if (
                        line.lstrip().startswith('<?xml version="1.0"?>')
                        or line.lstrip().startswith('<cml xmlns="http://www.xml-cml.org/schema')
                        or line.lstrip().startswith("</cml>")
                    ):
                        continue
                    lines.append(line)
                    if line.lstrip().startswith("</molecule>"):
                        yield lines
                        lines = []

        header_lines = ['<?xml version="1.0"?>\n', '<cml xmlns="http://www.xml-cml.org/schema">\n']
        footer_line = ["</cml>\n"]

        def _write_part_cml_file(accumulated_lines):
            part_dir = subdir_generator_function()
            part_path = os.path.join(part_dir, os.path.basename(input_files[0]))
            with open(part_path, "w") as part_file:
                part_file.writelines(header_lines)
                part_file.writelines(accumulated_lines)
                part_file.writelines(footer_line)

        try:
            cml_records = _read_cml_records(input_files[0])
            cml_lines_accumulated = []
            for counter, cml_record in enumerate(cml_records, start=1):
                cml_lines_accumulated.extend(cml_record)
                if counter % chunk_size == 0:
                    _write_part_cml_file(cml_lines_accumulated)
                    cml_lines_accumulated = []
            if cml_lines_accumulated:
                _write_part_cml_file(cml_lines_accumulated)
        except Exception as e:
            log.error("Unable to split files: %s", unicodify(e))
            raise

    @staticmethod
    def merge(split_files: List[str], output_file: str) -> None:
        """
        Merging CML files.
        """
        if len(split_files) == 1:
            # For one file only, use base class method (move/copy)
            return Text.merge(split_files, output_file)
        if not split_files:
            raise ValueError(f"Given no CML files, {split_files!r}, to merge into {output_file}")
        with open(output_file, "w") as out:
            for filename in split_files:
                with open(filename) as handle:
                    header = handle.readline()
                    if not header:
                        raise ValueError(f"CML file {filename} was empty")
                    if not header.lstrip().startswith('<?xml version="1.0"?>'):
                        out.write(header)
                        raise ValueError(f"{filename} is not a valid XML file!")
                    line = handle.readline()
                    header += line
                    if not line.lstrip().startswith('<cml xmlns="http://www.xml-cml.org/schema'):
                        out.write(header)
                        raise ValueError(f"{filename} is not a CML file!")
                    molecule_found = False
                    for line in handle.readlines():
                        # We found two required header lines, the next line should start with <molecule >
                        if line.lstrip().startswith("</cml>"):
                            continue
                        if line.lstrip().startswith("<molecule"):
                            molecule_found = True
                        if molecule_found:
                            out.write(line)
            out.write("</cml>\n")


class GRO(GenericMolFile):
    """
    GROMACS structure format.
    https://manual.gromacs.org/current/reference-manual/file-formats.html#gro
    """

    file_ext = "gro"

    def sniff_prefix(self, file_prefix: FilePrefix) -> bool:
        """
        Try to guess if the file is a GRO file.

        >>> from galaxy.datatypes.sniff import get_test_fname
        >>> fname = get_test_fname('5e5z.gro')
        >>> GRO().sniff_prefix(fname)
        True
        >>> fname = get_test_fname('5e5z.pdb')
        >>> GRO().sniff_prefix(fname)
        False
        """
        headers = get_headers(file_prefix, sep="\n", count=300)
        try:
            int(headers[1][0])  # the second line should just be the number of atoms
        except ValueError:
            return False
        for line in headers[2:-1]:  # skip the first, second and last lines
            if not re.search(
                r"^[0-9 ]{5}[a-zA-Z0-9 ]{10}[0-9 ]{5}[0-9 -]{4}\.[0-9]{3}[0-9 -]{4}\.[0-9]{3}[0-9 -]{4}\.[0-9]{3}",
                line[0],
            ):
                return False
        return True

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        if not dataset.dataset.purged:
            dataset.peek = get_file_peek(dataset.file_name)
            atom_number = int(dataset.peek.split("\n")[1])
            dataset.blurb = f"{atom_number} atoms"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"
