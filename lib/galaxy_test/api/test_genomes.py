from galaxy.exceptions import ObjectNotFound
from ._framework import ApiTestCase


class GenomesApiTestCase(ApiTestCase):

    def test_index(self):
        response = self._get('genomes')
        self._assert_status_code_is(response, 200)
        assert response.json()[0][0] == 'unspecified (?)'

    def test_show_invalid(self):
        response = self._get('genomes/invalid')
        self._assert_status_code_is(response, 404)
        assert response.json()['err_code'] == ObjectNotFound.err_code.code
