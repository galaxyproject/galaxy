from uuid import uuid4

from ._framework import ApiTestCase


def _form_xml(name: str) -> str:
    return f"""<form name="{name}" description="Test form description" type="user_info">
    <layout>
        <grid name="Grid 1"/>
    </layout>
    <fields>
        <field type="text" name="institution" label="Institution" required="true" layout="Grid 1"/>
        <field type="select" name="role" label="Role">
            <option value="student"/>
            <option value="researcher"/>
        </field>
    </fields>
</form>"""


class TestFormsApi(ApiTestCase):
    def test_create(self):
        name = f"test_form_{uuid4().hex}"
        response = self._post("forms", {"xml_text": _form_xml(name)}, admin=True, json=True)
        self._assert_status_code_is(response, 200)
        created = response.json()
        assert len(created) == 1
        form = created[0]
        self._assert_has_keys(form, "id", "name", "desc", "form_definition_current_id", "fields", "layout", "url")
        assert form["name"] == name
        assert form["desc"] == "Test form description"
        assert form["layout"] == ["Grid 1"]
        fields = form["fields"]
        assert len(fields) == 2
        assert fields[0]["name"] == "institution"
        assert fields[0]["type"] == "TextField"
        assert fields[0]["required"] == "required"
        assert fields[0]["layout"] == "0"
        assert fields[1]["name"] == "role"
        assert fields[1]["type"] == "SelectField"
        assert fields[1]["selectlist"] == ["student", "researcher"]

        index_response = self._get("forms", admin=True)
        self._assert_status_code_is(index_response, 200)
        assert form["id"] in [f["id"] for f in index_response.json()]

        show_response = self._get(f"forms/{form['id']}", admin=True)
        self._assert_status_code_is(show_response, 200)
        shown = show_response.json()
        assert shown["name"] == name
        assert shown["fields"] == fields

    def test_create_requires_admin(self):
        response = self._post("forms", {"xml_text": _form_xml(f"test_form_{uuid4().hex}")}, json=True)
        self._assert_status_code_is(response, 403)
