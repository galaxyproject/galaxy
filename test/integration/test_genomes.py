from galaxy.exceptions import (
    MissingDataError,
    ObjectNotFound,
)
from galaxy.visualization.genomes import Genome
from galaxy_test.driver import integration_util


class MockGenome:
    MOCK = {'a': 1, 'b': 2}

    def to_dict(*args, **kwgs):
        return MockGenome.MOCK


class GenomesTestCase(integration_util.IntegrationTestCase):

    def test_index(self):
        gen1, gen2 = 1, 2
        try:
            orig = self._app.genomes.get_dbkeys
            self._app.genomes.get_dbkeys = lambda *args, **kwgs: [gen1, gen2]
            response = self._get('genomes')
            self._assert_status_code_is(response, 200)
            assert response.json() == [gen1, gen2]
        except Exception as e:
            raise e
        finally:
            self._app.genomes.get_dbkeys = orig

    def test_show_valid(self):
        mock_key, mock_genome = 'foo', MockGenome()
        try:
            orig = self._app.genomes.genomes
            self._app.genomes.genomes = {mock_key: mock_genome}
            response = self._get(f'genomes/{mock_key}')
            self._assert_status_code_is(response, 200)
            assert response.json() == MockGenome.MOCK
        except Exception as e:
            raise e
        finally:
            self._app.genomes.genomes = orig

    def test_show_valid_missing(self):
        # Will call the real to_dict(), which should raise an error because foo has no len_file.
        mock_key, genome = 'foo', Genome('a', 'desc')
        try:
            orig = self._app.genomes.genomes
            self._app.genomes.genomes = {mock_key: genome}
            response = self._get(f'genomes/{mock_key}')
            self._assert_status_code_is(response, 500)
            assert response.json()['err_code'] == MissingDataError.err_code.code
        except Exception as e:
            raise e
        finally:
            self._app.genomes.genomes = orig

    def test_show_invalid(self):
        mock_key, mock_genome = 'foo', MockGenome()
        try:
            orig = self._app.genomes.genomes
            self._app.genomes.genomes = {mock_key: mock_genome}
            response = self._get('genomes/invalid')
            self._assert_status_code_is(response, 404)
            assert response.json()['err_code'] == ObjectNotFound.err_code.code
        except Exception as e:
            raise e
        finally:
            self._app.genomes.genomes = orig
