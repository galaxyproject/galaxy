import time

from requests import put

from ._framework import ApiTestCase

HIDDEN_DURING_UPLOAD_DATATYPE = "fli"


class DatatypesApiTestCase(ApiTestCase):
    def test_index(self):
        datatypes = self._index_datatypes()
        for common_type in ["tabular", "fasta"]:
            assert common_type in datatypes, f"{common_type} not in {datatypes}"

    def test_index_upload_only(self):
        # fli is not displayed in upload - so only show it if upload_only
        # is explicitly false.
        datatypes = self._index_datatypes(data={"upload_only": False})
        assert HIDDEN_DURING_UPLOAD_DATATYPE in datatypes

        datatypes = self._index_datatypes(data={"upload_only": True})
        assert HIDDEN_DURING_UPLOAD_DATATYPE not in datatypes

        datatypes = self._index_datatypes()
        assert HIDDEN_DURING_UPLOAD_DATATYPE not in datatypes

    def test_full_index(self):
        datatypes = self._index_datatypes(data={"extension_only": False})
        for datatype in datatypes:
            self._assert_has_keys(datatype, "extension", "description", "description_url")
            assert datatype["extension"] != HIDDEN_DURING_UPLOAD_DATATYPE

    def test_mapping(self):
        response = self._get("datatypes/mapping")
        self._assert_status_code_is(response, 200)
        mapping_dict = response.json()
        self._assert_has_keys(mapping_dict, "ext_to_class_name", "class_to_classes")

    def test_types_and_mapping(self):
        response = self._get("datatypes/types_and_mapping")
        self._assert_status_code_is(response, 200)
        response_dict = response.json()
        self._assert_has_keys(response_dict, "datatypes", "datatypes_mapping")
        mapping_dict = response_dict["datatypes_mapping"]
        self._assert_has_keys(mapping_dict, "ext_to_class_name", "class_to_classes")

        datatypes = response_dict["datatypes"]
        for common_type in ["tabular", "fasta"]:
            assert common_type in datatypes, f"{common_type} not in {datatypes}"

    def test_sniffers(self):
        response = self._get("datatypes/sniffers")
        self._assert_status_code_is(response, 200)
        sniffer_list = response.json()
        owl_index = sniffer_list.index("galaxy.datatypes.xml:Owl")
        xml_index = sniffer_list.index("galaxy.datatypes.xml:GenericXml")
        assert owl_index < xml_index

    def test_converters(self):
        response = self._get("datatypes/converters")
        self._assert_status_code_is(response, 200)
        converters_list = response.json()
        found_fasta_to_tabular = False

        for converter in converters_list:
            self._assert_has_key(converter, "source", "target", "tool_id")
            if converter["source"] == "fasta" and converter["target"] == "tabular":
                found_fasta_to_tabular = True

        assert found_fasta_to_tabular

    def test_converter_present_after_toolbox_reload(self):
        response = self._get("tools", data={"tool_id": "CONVERTER_fasta_to_tabular"})
        self._assert_status_code_is(response, 200)
        converters = len(response.json())
        assert converters == 1
        url = self._api_url("configuration/toolbox")
        put_response = put(url, params=dict(key=self.master_api_key))
        self._assert_status_code_is(put_response, 200)
        time.sleep(2)
        response = self._get("tools", data={"tool_id": "CONVERTER_fasta_to_tabular"})
        self._assert_status_code_is(response, 200)
        assert converters == len(response.json())

    def test_edam_formats(self):
        response = self._get("datatypes/edam_formats")
        self._assert_status_code_is(response, 200)
        edam_formats = response.json()
        assert isinstance(edam_formats, dict)
        assert edam_formats["ab1"] == "format_3000"

    def test_edam_data(self):
        response = self._get("datatypes/edam_data")
        self._assert_status_code_is(response, 200)
        edam_data = response.json()
        assert isinstance(edam_data, dict)
        assert edam_data["ab1"] == "data_0924"

    def _index_datatypes(self, data=None):
        data = data or {}
        response = self._get("datatypes", data=data)
        self._assert_status_code_is(response, 200)
        datatypes = response.json()
        assert isinstance(datatypes, list)
        return datatypes
