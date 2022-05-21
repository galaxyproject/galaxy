"""
Functionality for dealing with dbkeys.
"""
import logging
import os.path
import re
from json import loads

from galaxy.util import (
    galaxy_directory,
    sanitize_lists_to_string,
    unicodify,
)

log = logging.getLogger(__name__)


def read_dbnames(filename):
    """Read build names from file"""
    db_names = []
    try:
        ucsc_builds = {}
        man_builds = []  # assume these are integers
        name_to_db_base = {}
        if filename is None:
            # Should only be happening with the galaxy.tools.parameters.basic:GenomeBuildParameter docstring unit test
            filename = os.path.join(galaxy_directory(), "tool-data", "shared", "ucsc", "builds.txt.sample")
        for line in open(filename):
            try:
                if line[0:1] == "#":
                    continue
                fields = line.replace("\r", "").replace("\n", "").split("\t")
                # Special case of unspecified build is at top of list
                if fields[0] == "?":
                    db_names.insert(0, (fields[0], fields[1]))
                    continue
                try:  # manual build (i.e. microbes)
                    int(fields[0])
                    man_builds.append((fields[1], fields[0]))
                except Exception:  # UCSC build
                    db_base = fields[0].rstrip("0123456789")
                    if db_base not in ucsc_builds:
                        ucsc_builds[db_base] = []
                        name_to_db_base[fields[1]] = db_base
                    # we want to sort within a species numerically by revision number
                    build_rev = re.compile(r"\d+$")
                    try:
                        build_rev = int(build_rev.findall(fields[0])[0])
                    except Exception:
                        build_rev = 0
                    ucsc_builds[db_base].append((build_rev, fields[0], fields[1]))
            except Exception:
                continue
        sort_names = sorted(name_to_db_base.keys())
        for name in sort_names:
            db_base = name_to_db_base[name]
            ucsc_builds[db_base].sort()
            ucsc_builds[db_base].reverse()
            ucsc_builds[db_base] = [(build, name) for _, build, name in ucsc_builds[db_base]]
            db_names = list(db_names + ucsc_builds[db_base])
        man_builds.sort()
        man_builds = [(build, name) for name, build in man_builds]
        db_names = list(db_names + man_builds)
    except Exception as e:
        log.error("ERROR: Unable to read builds file: %s", unicodify(e))
    return db_names


class GenomeBuilds:
    default_value = "?"
    default_name = "unspecified (?)"

    def __init__(self, app, data_table_name="__dbkeys__", load_old_style=True):
        self._app = app
        self._data_table_name = data_table_name
        self._static_chrom_info_path = app.config.len_file_path
        # A dbkey can be listed multiple times, but with different names, so we can't use dictionaries for lookups
        if load_old_style:
            self._static_dbkeys = list(read_dbnames(app.config.builds_file_path))
        else:
            self._static_dbkeys = []

    def get_genome_build_names(self, trans=None):
        # FIXME: how to deal with key duplicates?
        rval = [(self.default_value, self.default_name)]
        # load user custom genome builds
        if trans is not None:
            if trans.history:
                # This is a little bit Odd. We are adding every .len file in the current history to dbkey list,
                # but this is previous behavior from trans.db_names, so we'll continue to do it.
                # It does allow one-off, history specific dbkeys to be created by a user. But we are not filtering,
                # so a len file will be listed twice (as the build name and again as dataset name),
                # if custom dbkey creation/conversion occurred within the current history.
                datasets = trans.sa_session.query(self._app.model.HistoryDatasetAssociation).filter_by(
                    deleted=False, history_id=trans.history.id, extension="len"
                )
                for dataset in datasets:
                    rval.append((dataset.dbkey, f"{dataset.name} ({dataset.dbkey}) [History]"))
            user = trans.user
            if user and hasattr(user, "preferences") and "dbkeys" in user.preferences:
                user_keys = loads(user.preferences["dbkeys"])
                for key, chrom_dict in user_keys.items():
                    rval.append((key, f"{chrom_dict['name']} ({key}) [Custom]"))
        # Load old builds.txt static keys
        rval.extend(self._static_dbkeys)
        # load dbkeys from dbkey data table
        dbkey_table = self._app.tool_data_tables.get(self._data_table_name, None)
        if dbkey_table is not None:
            for field_dict in dbkey_table.get_named_fields_list():
                rval.append((field_dict["value"], field_dict["name"]))
        return rval

    def get_chrom_info(self, dbkey, trans=None, custom_build_hack_get_len_from_fasta_conversion=True):
        # FIXME: flag to turn off custom_build_hack_get_len_from_fasta_conversion should not be required
        chrom_info = None
        db_dataset = None
        # Collect chromInfo from custom builds
        if trans:
            db_dataset = trans.db_dataset_for(dbkey)
            if db_dataset:
                chrom_info = db_dataset.file_name
            else:
                # Do Custom Build handling
                if (
                    trans.user
                    and ("dbkeys" in trans.user.preferences)
                    and (dbkey in loads(trans.user.preferences["dbkeys"]))
                ):
                    custom_build_dict = loads(trans.user.preferences["dbkeys"])[dbkey]
                    # HACK: the attempt to get chrom_info below will trigger the
                    # fasta-to-len converter if the dataset is not available or,
                    # which will in turn create a recursive loop when
                    # running the fasta-to-len tool. So, use a hack in the second
                    # condition below to avoid getting chrom_info when running the
                    # fasta-to-len converter.
                    if "fasta" in custom_build_dict and custom_build_hack_get_len_from_fasta_conversion:
                        # Build is defined by fasta; get len file, which is obtained from converting fasta.
                        build_fasta_dataset = trans.sa_session.query(trans.app.model.HistoryDatasetAssociation).get(
                            custom_build_dict["fasta"]
                        )
                        chrom_info = build_fasta_dataset.get_converted_dataset(trans, "len").file_name
                    elif "len" in custom_build_dict:
                        # Build is defined by len file, so use it.
                        chrom_info = (
                            trans.sa_session.query(trans.app.model.HistoryDatasetAssociation)
                            .get(custom_build_dict["len"])
                            .file_name
                        )
        # Check Data table
        if not chrom_info:
            dbkey_table = self._app.tool_data_tables.get(self._data_table_name, None)
            if dbkey_table is not None:
                chrom_info = dbkey_table.get_entry("value", dbkey, "len_path", default=None)
        # use configured server len path
        if not chrom_info:
            # Default to built-in build.
            # Since we are using an unverified dbkey, we will sanitize the dbkey before use
            chrom_info = os.path.join(self._static_chrom_info_path, f"{sanitize_lists_to_string(dbkey)}.len")
        chrom_info = os.path.abspath(chrom_info)
        return (chrom_info, db_dataset)
