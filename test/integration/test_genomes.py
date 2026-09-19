import os
import tempfile
from unittest.mock import patch

from galaxy.exceptions import (
    ObjectNotFound,
    ReferenceDataError,
)
from galaxy_test.driver import integration_util

BUILDS_DATA = (
    "?\tunspecified (?)",
    "hg_test\tdescription of hg_test",
    "hg_test_nolen\tdescription of hg_test_nolen",
)

LEN_DATA = (
    "chr1\t248956422",
    "chr2\t242193529",
    "chr3\t198295559",
)


def get_key(has_len_file=True):
    pos = 1 if has_len_file else 2
    return BUILDS_DATA[pos].split("\t")[0]


class TestGenomes(integration_util.IntegrationTestCase):
    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        genomes_dir = cls.temp_config_dir("test_genomes")
        os.makedirs(genomes_dir)
        cls._setup_builds_file(config, genomes_dir)
        cls._setup_len_file(config, genomes_dir)

    @classmethod
    def _setup_builds_file(cls, config, genomes_dir):
        """Create builds file + set config option."""
        builds_file_path = os.path.join(genomes_dir, "builds.txt")
        config["builds_file_path"] = builds_file_path
        with open(builds_file_path, "w") as f:
            f.write("\n".join(BUILDS_DATA))

    @classmethod
    def _setup_len_file(cls, config, genomes_dir):
        """Create len file + set config option."""
        config["len_file_path"] = genomes_dir  # the config option is a dir
        key = get_key()
        len_file_path = os.path.join(genomes_dir, f"{key}.len")
        with open(len_file_path, "w") as f:
            f.write("\n".join(LEN_DATA))

    def test_index(self):
        response = self._get("genomes")
        self._assert_status_code_is(response, 200)
        rval = response.json()
        expected_data = [item.split("\t")[::-1] for item in BUILDS_DATA]
        assert rval == expected_data

    def test_show_valid(self):
        key = get_key()
        response = self._get(f"genomes/{key}")
        self._assert_status_code_is(response, 200)
        rval = response.json()
        assert rval["id"] == key
        assert len(rval["chrom_info"]) == len(LEN_DATA)

    def test_show_valid_no_refdata(self):
        key = get_key(has_len_file=False)
        response = self._get(f"genomes/{key}")
        self._assert_status_code_is(response, 500)
        assert response.json()["err_code"] == ReferenceDataError.err_code.code

    def test_show_invalid(self):
        response = self._get("genomes/invalid")
        self._assert_status_code_is(response, 404)
        assert response.json()["err_code"] == ObjectNotFound.err_code.code

    def test_sequences(self):
        class RefDataMock:
            sequence = "test-value"

        key = get_key()
        with (
            patch.object(self._app.genomes, "has_reference_data", return_value=True),
            patch.object(self._app.genomes, "_get_reference_data", return_value=RefDataMock()),
        ):
            response = self._get(f"genomes/{key}/sequences")
            self._assert_status_code_is(response, 200)
            assert response.content == bytes(RefDataMock.sequence, "utf-8")

    def test_sequences_no_data(self):
        key = get_key()
        with patch.object(self._app.genomes, "has_reference_data", return_value=False):
            response = self._get(f"genomes/{key}/sequences")
            self._assert_status_code_is(response, 500)
            assert response.json()["err_code"] == ReferenceDataError.err_code.code

    def test_indexes(self):
        mock_key, mock_content, index_type, suffix = "mykey", "mydata", "fasta_indexes", ".fai"
        # write some data to a tempfile
        with tempfile.NamedTemporaryFile(dir=self._tempdir, suffix=suffix, mode="w", delete=False) as tf:
            tf.write(mock_content)
        # make a mock containing the path to the tempfile
        tmpfile_path = tf.name[: -len(suffix)]  # chop off the extention
        mock_data = [[mock_key, tmpfile_path]]
        with patch.object(self._app.tool_data_tables.data_tables[index_type], "data", new=mock_data):
            response = self._get(f"genomes/{mock_key}/indexes?type={index_type}")
            self._assert_status_code_is(response, 200)
            assert response.content == bytes(mock_content, "utf-8")
