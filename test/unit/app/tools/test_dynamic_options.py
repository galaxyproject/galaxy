import pytest

from galaxy.app_unittest_utils import tools_support
from galaxy.app_unittest_utils.galaxy_mock import MockApp
from galaxy.tools.data import ToolDataTableManager
from galaxy.tools.parameters import dynamic_options
from galaxy.tools.parameters.dynamic_options import DynamicOptions
from galaxy.tools.parameters.options import ParameterOption
from galaxy.tools.parameters.workflow_utils import (
    ConnectedValue,
    RuntimeValue,
)
from galaxy.util import XML
from galaxy.util.bunch import Bunch
from galaxy.util.expressions import ExpressionContext
from galaxy.util.unittest import TestCase
from galaxy.work.context import WorkRequestContext


def get_from_url_option():
    tool_param = Bunch(
        tool=Bunch(
            app=Bunch(),
        ),
    )

    return DynamicOptions(
        XML("""
<options from_url="https://usegalaxy.org/api/genomes/dm6" request_method="POST">
    <request_headers type="json">
        {"x-api-key": "${__user__.extra_preferences.resource_api_key if $__user__ else "anon"}"}
    </request_headers>
    <request_body type="json">
        {"some_key": "some_value"}
    </request_body>
    <postprocess_expression type="ecma5.1"><![CDATA[${
        if (inputs) {
            return Object.values(inputs.chrom_info).map((v) => [v.chrom, v.len])
        } else {
            return [["The fallback value", "default"]]
        }
    }]]></postprocess_expression>
</options>
"""),
        tool_param,
    )


def test_dynamic_option_parsing():
    from_url_option = get_from_url_option()
    assert from_url_option.from_url_options
    assert from_url_option.from_url_options.from_url == "https://usegalaxy.org/api/genomes/dm6"


def test_dynamic_option_cache():
    app = MockApp()
    trans = WorkRequestContext(app=app)
    from_url_option = get_from_url_option()
    options = from_url_option.from_url_options
    assert options
    args = (options.from_url, options.request_method, options.request_body, '{"x-api-key": "anon"}')
    trans.set_cache_value(
        args,
        {
            "id": "dm6",
            "reference": True,
            "chrom_info": [{"chrom": "chr2L", "len": 23513712}],
            "prev_chroms": False,
            "next_chroms": False,
            "start_index": 0,
        },
    )
    assert from_url_option.get_options(trans, {}) == [ParameterOption("chr2L", "23513712", False)]


DEPENDENT_FROM_URL_OPTIONS = """
<options from_url="https://example.org/crops/$crop/genotype_sets?year=$sec.year" request_method="POST" depends_on="crop,sec.year">
    <request_headers type="json">
        {"x-crop": "$crop"}
    </request_headers>
    <request_body type="json">
        {"crop": "$crop", "year": "$sec.year"}
    </request_body>
</options>
"""


def get_dependent_from_url_option(options_xml: str = DEPENDENT_FROM_URL_OPTIONS) -> DynamicOptions:
    return DynamicOptions(XML(options_xml), Bunch(tool=Bunch(app=Bunch())))


@pytest.fixture
def recorded_requests(monkeypatch):
    requests = []

    def request(**kwargs):
        requests.append(kwargs)
        return [["Set A", "a"], ["Set B", "b"]]

    monkeypatch.setattr(dynamic_options, "request", request)
    return requests


def test_from_url_depends_on_values_are_encoded_per_target(recorded_requests):
    trans = WorkRequestContext(app=MockApp())
    crop = 'ma/ize "x"?#&'
    other_values = ExpressionContext({"sec": {"year": 2020}}, ExpressionContext({"crop": crop}))
    options = get_dependent_from_url_option().get_options(trans, other_values)
    assert options == [ParameterOption("Set A", "a", False), ParameterOption("Set B", "b", False)]
    (request,) = recorded_requests
    assert request["url"] == "https://example.org/crops/ma%2Fize%20%22x%22%3F%23%26/genotype_sets?year=2020"
    assert request["data"] == {"crop": crop, "year": "2020"}
    assert request["headers"] == {"x-crop": crop}


def test_from_url_depends_on_joins_multiple_values(recorded_requests):
    trans = WorkRequestContext(app=MockApp())
    get_dependent_from_url_option().get_options(trans, {"crop": ["maize", "rice"], "sec": {"year": 2020}})
    (request,) = recorded_requests
    assert request["url"] == "https://example.org/crops/maize,rice/genotype_sets?year=2020"
    assert request["data"] == {"crop": "maize,rice", "year": "2020"}


@pytest.mark.parametrize(
    "other_values",
    [
        {"sec": {"year": 2020}},
        {"crop": None, "sec": {"year": 2020}},
        {"crop": "", "sec": {"year": 2020}},
        {"crop": [], "sec": {"year": 2020}},
        {"crop": RuntimeValue(), "sec": {"year": 2020}},
        {"crop": ConnectedValue(), "sec": {"year": 2020}},
        {"crop": {"__class__": "ConnectedValue"}, "sec": {"year": 2020}},
        {"crop": "maize"},
        {"crop": "maize", "sec": {"year": None}},
    ],
)
def test_from_url_depends_on_unset_value_makes_no_request(recorded_requests, other_values):
    trans = WorkRequestContext(app=MockApp())
    assert get_dependent_from_url_option().get_options(trans, other_values) == []
    assert recorded_requests == []


def test_from_url_depends_on_is_a_dependency():
    assert get_dependent_from_url_option().get_dependency_names() == ["crop", "sec.year"]


@pytest.mark.parametrize(
    "from_url",
    [
        "https://example.org/crops/$crop",
        "https://example.org/crops?crop=${crop}",
        "https://example.org#$crop",
        "${__user__.extra_preferences.server}/crops/$crop",
    ],
)
def test_from_url_depends_on_in_path_or_query(from_url):
    get_dependent_from_url_option(f'<options from_url="{from_url}" depends_on="crop"/>')


@pytest.mark.parametrize(
    "from_url",
    [
        "https://$crop.example.org/",
        "https://example.org$crop/",
        "https://${crop}/",
        "https://user:$crop@example.org/",
        "$crop/crops",
    ],
)
def test_from_url_depends_on_in_host_is_rejected(from_url):
    with pytest.raises(ValueError, match="scheme or host"):
        get_dependent_from_url_option(f'<options from_url="{from_url}" depends_on="crop"/>')


def test_hda_to_table_entries_without_dbkey():
    """A data-manager bundle whose table has no dbkey column (e.g. motus,
    dada2_species) must still yield a table entry - keyed by its ``value``
    column - so it can be consumed by a downstream tool in a workflow (the
    data-manager bundle chain). Previously such entries were dropped, leaving
    the downstream select param with "no legal values defined".

    The motus DM records the entry as a bare dict (not a one-element list), so
    exercise that shape here - iterating it directly would yield column names."""
    hda = Bunch(
        extra_files_path="/bundle/extra",
        _metadata={
            "data_tables": {
                "motus_db_versioned": {
                    "value": "db_from_2026-04-27T094930Z",
                    "version": "3.1.0",
                    "name": "mOTUs DB version 3.1.0",
                    "path": "db_from_2026-04-27T094930Z",
                }
            }
        },
    )
    entries = DynamicOptions.hda_to_table_entries(hda, "motus_db_versioned")
    assert list(entries) == ["db_from_2026-04-27T094930Z"]
    entry = entries["db_from_2026-04-27T094930Z"]
    # the path column is relocated under the bundle's extra_files_path
    assert entry["path"] == "/bundle/extra/db_from_2026-04-27T094930Z"
    assert entry["__hda__"] is hda


def test_hda_to_table_entries_prefers_dbkey():
    """When the table has a dbkey column it is still used as the entry key."""
    hda = Bunch(
        extra_files_path="/bundle/extra",
        _metadata={
            "data_tables": {
                "metaphlan_database_versioned": [
                    {
                        "value": "mpa_vJan21_CHOCOPhlAnSGB_202103-04042023",
                        "name": "MetaPhlAn clade-specific marker genes",
                        "dbkey": "mpa_vJan21_CHOCOPhlAnSGB_202103",
                        "path": "mpa_vJan21_CHOCOPhlAnSGB_202103",
                        "db_version": "SGB",
                    }
                ]
            }
        },
    )
    entries = DynamicOptions.hda_to_table_entries(hda, "metaphlan_database_versioned")
    assert list(entries) == ["mpa_vJan21_CHOCOPhlAnSGB_202103"]


def test_get_options_handles_missing_name_column():
    """Must fall back to value column if display name is missing."""
    tool_param = Bunch(tool=Bunch(app=Bunch()))

    opts = DynamicOptions(XML("<options/>"), tool_param)
    opts.columns = {"value": 0}

    opts.file_fields = [["hg38"], ["mm10"]]

    trans = WorkRequestContext(app=MockApp())
    options = opts.get_options(trans, {})

    # No KeyError, and name falls back to value when no name column exists.
    assert options == [
        ParameterOption("hg38", "hg38", False),
        ParameterOption("mm10", "mm10", False),
    ]


def test_get_field_by_name_for_value_uses_first_entry_for_duplicate_values():
    """Duplicate values must not be joined into a comma separated path."""
    tool_param = Bunch(tool=Bunch(app=Bunch()))

    opts = DynamicOptions(XML("<options/>"), tool_param)
    opts.columns = {"value": 0, "name": 1, "path": 2}
    opts.largest_index = 2
    opts.file_fields = [
        ["hg38", "Human (hg38)", "/local/hg38.fa"],
        ["hg38", "Human (hg38)", "/idc/hg38.fa"],
        ["mm10", "Mouse (mm10)", "/local/mm10.fa"],
    ]

    trans = WorkRequestContext(app=MockApp())
    assert opts.get_field_by_name_for_value("path", "hg38", trans, {}) == ["/local/hg38.fa"]
    # multiple selected values still resolve to one entry each
    assert opts.get_field_by_name_for_value("path", ["hg38", "mm10"], trans, {}) == [
        "/local/hg38.fa",
        "/local/mm10.fa",
    ]
    assert opts.get_field_by_name_for_value("path", "unknown", trans, {}) == []


@pytest.mark.parametrize("version", ["4.3", "5.0", "5.1"])
def test_merged_data_table_filters_versions_before_resolving_value(tmp_path, version):
    configs = []
    for source, versions in (("local", ["4.3"]), ("repository", ["5.0", "5.1"])):
        loc = tmp_path / f"{source}.loc"
        loc.write_text("".join(f"hg38\tHuman (hg38)\t{v}\t/indexes/{v}/hg38\n" for v in versions))
        config = tmp_path / f"{source}.xml"
        config.write_text(f"""<tables>
  <table name="snpeff">
    <columns>value, name, version, path</columns>
    <file path="{loc}" />
  </table>
</tables>""")
        configs.append(str(config))
    app = MockApp()
    app.tool_data_tables = ToolDataTableManager(tmp_path, ",".join(configs))
    opts = DynamicOptions(
        XML(f"""<options from_data_table="snpeff">
  <filter type="static_value" column="version" value="{version}" />
</options>"""),
        Bunch(tool=Bunch(app=app)),
    )
    trans = WorkRequestContext(app=app)
    for reload in (False, True):
        if reload:
            app.tool_data_tables.reload_tables()
        assert opts.get_options(trans, {}) == [ParameterOption("Human (hg38)", "hg38", False)]
        assert opts.get_field_by_name_for_value("path", "hg38", trans, {}) == [f"/indexes/{version}/hg38"]


DEPENDENT_FROM_URL_TOOL = """<tool id="test_tool" name="Test Tool" version="1.0" profile="24.0">
    <command>echo '$genotype_set'</command>
    <inputs>
        <param name="crop" type="select">
            <option value="maize">Maize</option>
        </param>
        <param name="unrelated" type="text"/>
        <section name="sec" title="Section">
            <param name="year" type="integer" value="2020"/>
        </section>
        <conditional name="cond">
            <param name="kind" type="select">
                <option value="a">A</option>
                <option value="b">B</option>
            </param>
            <when value="a">
                <param name="variety" type="text"/>
            </when>
            <when value="b">
                <param name="variety" type="text"/>
            </when>
        </conditional>
        <param name="genotype_set" type="select">
            <options from_url="https://example.org/crops/$crop/$sec.year/$cond.kind/$cond.variety" depends_on="DEPENDS_ON"/>
        </param>
    </inputs>
    <outputs/>
</tool>
"""


class TestFromUrlDependsOnRefresh(TestCase, tools_support.UsesTools):
    def setUp(self):
        super().setUp()
        self.setup_app()

    def tearDown(self):
        self.tear_down_app()

    def test_depends_on_refreshes_named_inputs(self):
        tool = self._init_tool(DEPENDENT_FROM_URL_TOOL.replace("DEPENDS_ON", "crop,sec.year,cond.kind,cond.variety"))
        sec = tool.inputs["sec"]
        cond = tool.inputs["cond"]
        assert tool.inputs["crop"].refresh_on_change
        assert sec.inputs["year"].refresh_on_change
        assert cond.test_param.refresh_on_change
        assert all(case.inputs["variety"].refresh_on_change for case in cond.cases)
        assert not tool.inputs["unrelated"].refresh_on_change

    def test_depends_on_unknown_input_fails_to_load(self):
        with pytest.raises(AssertionError, match="Could not find dependency 'sec.month'"):
            self._init_tool(DEPENDENT_FROM_URL_TOOL.replace("DEPENDS_ON", "crop,sec.month"))
