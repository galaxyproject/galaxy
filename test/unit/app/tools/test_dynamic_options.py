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
        XML(
            """
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
"""
        ),
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
