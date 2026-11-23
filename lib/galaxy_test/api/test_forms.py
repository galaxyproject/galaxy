from ._framework import ApiTestCase

FORM_XML = """<form name="api test form" description="created through the API" type="user_info">
    <layout>
        <grid name="g1"/>
    </layout>
    <fields>
        <field name="affiliation" label="Affiliation" type="text" layout="g1"/>
    </fields>
</form>"""


class TestFormsApi(ApiTestCase):
    def test_create_from_xml(self):
        response = self._post("forms", {"xml_text": FORM_XML}, admin=True, json=True)
        self._assert_status_code_is(response, 200)
        form = response.json()[0]
        assert form["name"] == "api test form"
        assert form["desc"] == "created through the API"
        assert form["layout"] == ["g1"]
        assert [field["name"] for field in form["fields"]] == ["affiliation"]

        show_response = self._get(f"forms/{form['id']}", admin=True)
        self._assert_status_code_is(show_response, 200)
        assert show_response.json()["name"] == "api test form"
