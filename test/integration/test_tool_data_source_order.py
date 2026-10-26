"""Integration tests for administrator-configured tool data table source order."""

import os

from galaxy_test.driver import integration_util

TABLE_XML = """<tables><table name="ordered_refs">
  <columns>value, name, path</columns><file path="{loc}" />
</table></tables>"""


def _write_source(directory, name, rows):
    loc = os.path.join(directory, f"{name}.loc")
    with open(loc, "w") as f:
        f.write(rows)
    config = os.path.join(directory, f"{name}.xml")
    with open(config, "w") as f:
        f.write(TABLE_XML.format(loc=loc))
    return config


class TestToolDataSourceOrderIntegration(integration_util.IntegrationTestCase):
    require_admin_user = True
    source_dir: str
    managed: str

    @classmethod
    def handle_galaxy_config_kwds(cls, config):
        super().handle_galaxy_config_kwds(config)
        cls.source_dir = cls.temp_config_dir("ordered_tool_data")
        os.makedirs(cls.source_dir, exist_ok=True)
        cls.managed = os.path.join(cls.source_dir, "managed.xml")
        with open(cls.managed, "w") as f:
            f.write("<tables />")
        external = _write_source(cls.source_dir, "external", "hg38\tHuman\t/external\n")
        config["tool_data_path"] = cls.source_dir
        config["shed_tool_data_table_config"] = cls.managed
        config["tool_data_table_config_path"] = [cls.managed, external]

    def _paths(self):
        response = self._get("tool_data/ordered_refs")
        response.raise_for_status()
        return [row[2] for row in response.json()["fields"]]

    def test_registration_lands_in_configured_managed_position(self):
        assert self._paths() == ["/external"]
        incoming = _write_source(self.source_dir, "incoming", "mm10\tMouse\t/incoming\n")
        _, error = self._app.tool_data_tables.add_new_entries_from_config_file(
            incoming, None, self.managed, persist=True
        )
        assert not error
        assert self._paths() == ["/incoming", "/external"]
        self._app.tool_data_tables.reload_tables()
        assert self._paths() == ["/incoming", "/external"]
