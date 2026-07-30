from galaxy.app_unittest_utils.galaxy_mock import MockApp
from galaxy.tools.parameters.dynamic_options import DynamicOptions
from galaxy.tools.parameters.options import ParameterOption
from galaxy.util import XML
from galaxy.util.bunch import Bunch
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


def test_hda_to_table_entries_without_dbkey():
    """A data-manager bundle whose table has no dbkey column (e.g. motus,
    dada2_species) must still yield a table entry - keyed by its ``value``
    column - so it can be consumed by a downstream tool in a workflow (the
    data-manager bundle chain). Previously such entries were dropped, leaving
    the downstream select param with "no legal values defined"."""
    hda = Bunch(
        extra_files_path="/bundle/extra",
        _metadata={
            "data_tables": {
                "motus_db_versioned": [
                    {
                        "value": "db_from_2026-04-27T094930Z",
                        "version": "3.1.0",
                        "name": "mOTUs DB version 3.1.0",
                        "path": "db_from_2026-04-27T094930Z",
                    }
                ]
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
