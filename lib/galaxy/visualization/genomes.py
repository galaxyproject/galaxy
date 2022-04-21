import logging
import os
import re
import sys
from json import loads
from typing import Dict

from bx.seq.twobit import TwoBitFile

from galaxy.exceptions import (
    ObjectNotFound,
    ReferenceDataError,
)
from galaxy.structured_app import StructuredApp
from galaxy.util.bunch import Bunch

log = logging.getLogger(__name__)

# FIXME: copied from tracks.py
# Message strings returned to browser
messages = Bunch(
    PENDING="pending",
    NO_DATA="no data",
    NO_CHROMOSOME="no chromosome",
    NO_CONVERTER="no converter",
    NO_TOOL="no tool",
    DATA="data",
    ERROR="error",
    OK="ok",
)


def decode_dbkey(dbkey):
    """Decodes dbkey and returns tuple ( username, dbkey )"""
    if isinstance(dbkey, str) and ":" in dbkey:
        return dbkey.split(":")
    else:
        return None, dbkey


class GenomeRegion:
    """
    A genomic region on an individual chromosome.
    """

    def __init__(self, chrom=None, start=0, end=0, sequence=None):
        self.chrom = chrom
        self.start = int(start)
        self.end = int(end)
        self.sequence = sequence

    def __str__(self):
        return f"{self.chrom}:{str(self.start)}-{str(self.end)}"

    @staticmethod
    def from_dict(obj_dict):
        return GenomeRegion(chrom=obj_dict["chrom"], start=obj_dict["start"], end=obj_dict["end"])

    @staticmethod
    def from_str(obj_str):
        # check for gene region
        gene_region = obj_str.split(":")

        # split gene region into components
        if len(gene_region) == 2:
            gene_interval = gene_region[1].split("-")

            # check length
            if len(gene_interval) == 2:
                return GenomeRegion(chrom=gene_region[0], start=gene_interval[0], end=gene_interval[1])

        # return genome region instance
        return GenomeRegion()


class Genome:
    """
    Encapsulates information about a known genome/dbkey.
    """

    def __init__(self, key, description, len_file=None, twobit_file=None):
        self.key = key
        self.description = description
        self.len_file = len_file
        self.twobit_file = twobit_file

    def to_dict(self, num=None, chrom=None, low=None):
        """
        Returns representation of self as a dictionary.
        """
        # if there's no len_file, there's nothing to return
        if not self.len_file:
            raise ReferenceDataError(f"len_file not set for {self.key}")

        def check_int(s):
            if s.isdigit():
                return int(s)
            else:
                return s

        def split_by_number(s):
            return [check_int(c) for c in re.split("([0-9]+)", s)]

        #
        # Parameter check, setting.
        #
        if num:
            num = int(num)
        else:
            num = sys.maxsize  # just a big number

        if low:
            low = int(low)
            if low < 0:
                low = 0
        else:
            low = 0

        #
        # Get chroms data:
        #   (a) chrom name, len;
        #   (b) whether there are previous, next chroms;
        #   (c) index of start chrom.
        #
        with open(self.len_file) as f:
            len_file_enumerate = enumerate(f)
            chroms = {}
            prev_chroms = False
            start_index = 0
            if chrom:
                # Use starting chrom to start list.
                found = False
                count = 0
                for line_num, line in len_file_enumerate:
                    if line.startswith("#"):
                        continue
                    name, len = line.split("\t")
                    if found:
                        chroms[name] = int(len)
                        count += 1
                    elif name == chrom:
                        # Found starting chrom.
                        chroms[name] = int(len)
                        count += 1
                        found = True
                        start_index = line_num
                        if line_num != 0:
                            prev_chroms = True
                    if count >= num:
                        break
            else:
                # Use low to start list.
                high = low + int(num)
                prev_chroms = low != 0
                start_index = low

                # Read chrom data from len file.
                for line_num, line in len_file_enumerate:
                    if line_num < low:
                        continue
                    if line_num >= high:
                        break
                    if line.startswith("#"):
                        continue
                    # LEN files have format:
                    #   <chrom_name><tab><chrom_length>
                    fields = line.split("\t")
                    chroms[fields[0]] = int(fields[1])

            # Set flag to indicate whether there are more chroms after list.
            next_chroms = False
            try:
                next(len_file_enumerate)
                next_chroms = True
            except StopIteration:
                # No more chroms to read.
                pass

            to_sort = [{"chrom": chrm, "len": length} for chrm, length in chroms.items()]
            to_sort.sort(key=lambda _: split_by_number(_["chrom"]))
            return {
                "id": self.key,
                "reference": self.twobit_file is not None,
                "chrom_info": to_sort,
                "prev_chroms": prev_chroms,
                "next_chroms": next_chroms,
                "start_index": start_index,
            }


class Genomes:
    """
    Provides information about available genome data and methods for manipulating that data.
    """

    def __init__(self, app: StructuredApp):
        self.app = app
        # Create list of genomes from app.genome_builds
        self.genomes: Dict[str, Genome] = {}
        # Store internal versions of data tables for twobit and __dbkey__
        self._table_versions = {"twobit": None, "__dbkeys__": None}
        self.reload_genomes()

    def reload_genomes(self):
        self.genomes = {}
        # Store table versions for later
        for table_name in self._table_versions.keys():
            table = self.app.tool_data_tables.get(table_name, None)
            if table is not None:
                self._table_versions[table_name] = table._loaded_content_version

        twobit_table = self.app.tool_data_tables.get("twobit", None)
        twobit_fields = {}
        if twobit_table is None:
            # Add genome data (twobit files) to genomes, directly from twobit.loc
            try:
                twobit_path = os.path.join(self.app.config.tool_data_path, "twobit.loc")
                with open(twobit_path) as f:
                    for line in f:
                        if line.startswith("#"):
                            continue
                        val = line.split()
                        if len(val) == 2:
                            key, path = val
                            twobit_fields[key] = path
            except OSError:
                # Thrown if twobit.loc does not exist.
                log.exception("Error reading twobit.loc")
        for key, description in self.app.genome_builds.get_genome_build_names():
            self.genomes[key] = Genome(key, description)
            # Add len files to genomes.
            self.genomes[key].len_file = self.app.genome_builds.get_chrom_info(key)[0]
            if self.genomes[key].len_file:
                if not os.path.exists(self.genomes[key].len_file):
                    self.genomes[key].len_file = None
            # Add genome data (twobit files) to genomes.
            if twobit_table is not None:
                self.genomes[key].twobit_file = twobit_table.get_entry("value", key, "path", default=None)
            elif key in twobit_fields:
                self.genomes[key].twobit_file = twobit_fields[key]

    def check_and_reload(self):
        # Check if tables have been modified, if so reload
        for table_name, table_version in self._table_versions.items():
            table = self.app.tool_data_tables.get(table_name, None)
            if table is not None and not table.is_current_version(table_version):
                return self.reload_genomes()

    def get_build(self, dbkey):
        """Returns build for the given key."""
        self.check_and_reload()
        rval = None
        if dbkey in self.genomes:
            rval = self.genomes[dbkey]
        return rval

    def get_dbkeys(self, user, chrom_info=False):
        """Returns all known dbkeys. If chrom_info is True, only dbkeys with
        chromosome lengths are returned."""
        self.check_and_reload()
        dbkeys = []

        # Add user's custom keys to dbkeys.
        if user and "dbkeys" in user.preferences:
            user_keys_dict = loads(user.preferences["dbkeys"])
            dbkeys.extend([(attributes["name"], key) for key, attributes in user_keys_dict.items()])

        # Add app keys to dbkeys.

        # If chrom_info is True, only include keys with len files (which contain chromosome info).
        if chrom_info:

            def filter_fn(b):
                return b.len_file is not None

        else:

            def filter_fn(b):
                return True

        dbkeys.extend([(genome.description, genome.key) for key, genome in self.genomes.items() if filter_fn(genome)])

        return dbkeys

    def chroms(self, trans, dbkey=None, num=None, chrom=None, low=None):
        """
        Returns a naturally sorted list of chroms/contigs for a given dbkey.
        Use either chrom or low to specify the starting chrom in the return list.
        """
        self.check_and_reload()
        # If there is no dbkey owner, default to current user.
        dbkey_owner, dbkey = decode_dbkey(dbkey)
        if dbkey_owner:
            dbkey_user = trans.sa_session.query(trans.app.model.User).filter_by(username=dbkey_owner).first()
        else:
            dbkey_user = trans.user

        #
        # Get/create genome object.
        #
        genome = None
        twobit_file = None

        # Look first in user's custom builds.
        if dbkey_user and "dbkeys" in dbkey_user.preferences:
            user_keys = loads(dbkey_user.preferences["dbkeys"])
            if dbkey in user_keys:
                dbkey_attributes = user_keys[dbkey]
                dbkey_name = dbkey_attributes["name"]

                # If there's a fasta for genome, convert to 2bit for later use.
                if "fasta" in dbkey_attributes:
                    build_fasta = trans.sa_session.query(trans.app.model.HistoryDatasetAssociation).get(
                        dbkey_attributes["fasta"]
                    )
                    len_file = build_fasta.get_converted_dataset(trans, "len").file_name
                    build_fasta.get_converted_dataset(trans, "twobit")
                    # HACK: set twobit_file to True rather than a file name because
                    # get_converted_dataset returns null during conversion even though
                    # there will eventually be a twobit file available for genome.
                    twobit_file = True
                # Backwards compatibility: look for len file directly.
                elif "len" in dbkey_attributes:
                    len_file = (
                        trans.sa_session.query(trans.app.model.HistoryDatasetAssociation)
                        .get(user_keys[dbkey]["len"])
                        .file_name
                    )
                if len_file:
                    genome = Genome(dbkey, dbkey_name, len_file=len_file, twobit_file=twobit_file)

        # Look in history and system builds.
        if not genome:
            # Look in history for chromosome len file.
            len_ds = trans.db_dataset_for(dbkey)
            if len_ds:
                genome = Genome(dbkey, dbkey_name, len_file=len_ds.file_name)
            # Look in system builds.
            elif dbkey in self.genomes:
                genome = self.genomes[dbkey]

        if not genome:
            raise ObjectNotFound(f"genome not found for key {dbkey}")

        return genome.to_dict(num=num, chrom=chrom, low=low)

    def has_reference_data(self, dbkey, dbkey_owner=None):
        """
        Returns true if there is reference data for the specified dbkey. If dbkey is custom,
        dbkey_owner is needed to determine if there is reference data.
        """
        self.check_and_reload()
        # Look for key in built-in builds.
        if dbkey in self.genomes and self.genomes[dbkey].twobit_file:
            # There is built-in reference data.
            return True

        # Look for key in owner's custom builds.
        if dbkey_owner and "dbkeys" in dbkey_owner.preferences:
            user_keys = loads(dbkey_owner.preferences["dbkeys"])
            if dbkey in user_keys:
                dbkey_attributes = user_keys[dbkey]
                if "fasta" in dbkey_attributes:
                    # Fasta + converted datasets can provide reference data.
                    return True

        return False

    def reference(self, trans, dbkey, chrom, low, high):
        """
        Return reference data for a build.
        """
        self.check_and_reload()
        # If there is no dbkey owner, default to current user.
        dbkey_owner, dbkey = decode_dbkey(dbkey)
        if dbkey_owner:
            dbkey_user = trans.sa_session.query(trans.app.model.User).filter_by(username=dbkey_owner).first()
        else:
            dbkey_user = trans.user

        if not self.has_reference_data(dbkey, dbkey_user):
            raise ReferenceDataError(f"No reference data for {dbkey}")

        #
        # Get twobit file with reference data.
        #
        twobit_file_name = None
        if dbkey in self.genomes:
            # Built-in twobit.
            twobit_file_name = self.genomes[dbkey].twobit_file
        else:
            user_keys = loads(dbkey_user.preferences["dbkeys"])
            dbkey_attributes = user_keys[dbkey]
            fasta_dataset = trans.sa_session.query(trans.app.model.HistoryDatasetAssociation).get(
                dbkey_attributes["fasta"]
            )
            msg = fasta_dataset.convert_dataset(trans, "twobit")
            if msg:
                return msg
            else:
                twobit_dataset = fasta_dataset.get_converted_dataset(trans, "twobit")
                twobit_file_name = twobit_dataset.file_name

        return self._get_reference_data(twobit_file_name, chrom, low, high)

    @staticmethod
    def _get_reference_data(twobit_file_name, chrom, low, high):
        # Read and return reference data.
        with open(twobit_file_name, "rb") as f:
            twobit = TwoBitFile(f)
            if chrom in twobit:
                seq_data = twobit[chrom].get(int(low), int(high))
                return GenomeRegion(chrom=chrom, start=low, end=high, sequence=seq_data)
