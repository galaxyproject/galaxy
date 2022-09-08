import pytest

from galaxy.tools.data import ToolDataTableManager

LOC_ALPHA_CONTENTS = """
data1	data1name	${__HERE__}/data1/entry.txt
data2	data2name	${__HERE__}/data2/entry.txt
"""


LOC_ALPHA_CONTENTS_V2 = """
data1	data1name	${__HERE__}/data1/entry.txt
data2	data2name	${__HERE__}/data2/entry.txt
data3	data3name	${__HERE__}/data3/entry.txt
"""


LOC_BETA_CONTENTS_1 = """
beta1	beta1name	${__HERE__}/beta1/entry.txt
"""


LOC_BETA_CONTENTS_2 = """
beta2	beta2name	${__HERE__}/beta2/entry.txt
"""


TOOL_DATA_TABLE_CONF_XML = """<tables>
  <table name="testalpha" comment_char="#">
    <columns>value, name, path</columns>
    <file path="${__HERE__}/testalpha.loc" />
  </table>
</tables>
"""


MERGED_TOOL_DATA_TABLE_CONF_XML_1 = """<tables>
  <table name="testbeta" comment_char="#">
    <columns>value, name, path</columns>
    <file path="${__HERE__}/testbeta1.loc" />
  </table>
</tables>
"""


MERGED_TOOL_DATA_TABLE_CONF_XML_2 = """<tables>
  <table name="testbeta" comment_char="#">
    <columns>value, name, path</columns>
    <file path="${__HERE__}/testbeta2.loc" />
  </table>
</tables>
"""


@pytest.fixture
def tdt_manager(tmp_path) -> ToolDataTableManager:
    _write_loc_files(tmp_path)
    conf = tmp_path / "tool_data_table_conf.xml"
    conf.write_text(TOOL_DATA_TABLE_CONF_XML)
    return ToolDataTableManager(tmp_path, conf)


@pytest.fixture
def merged_tdt_manager(tmp_path) -> ToolDataTableManager:
    _write_loc_files(tmp_path)
    conf1 = tmp_path / "tool_data_table_conf_1.xml"
    conf1.write_text(MERGED_TOOL_DATA_TABLE_CONF_XML_1)
    conf2 = tmp_path / "tool_data_table_conf_2.xml"
    conf2.write_text(MERGED_TOOL_DATA_TABLE_CONF_XML_2)
    return ToolDataTableManager(tmp_path, f"{conf1},{conf2}")


def _write_loc_files(tmp_path):
    loc1 = tmp_path / "testalpha.loc"
    loc1.write_text(LOC_ALPHA_CONTENTS)

    loc2 = tmp_path / "testbeta1.loc"
    loc2.write_text(LOC_BETA_CONTENTS_1)

    loc3 = tmp_path / "testbeta2.loc"
    loc3.write_text(LOC_BETA_CONTENTS_2)

    data1 = tmp_path / "data1"
    data1.mkdir()
    data1_entry = data1 / "entry.txt"
    data1_entry.write_text("This is data 1.")

    data2 = tmp_path / "data2"
    data2.mkdir()
    data2_entry = data2 / "entry.txt"
    data2_entry.write_text("This is data 2.")

    data3 = tmp_path / "data3"
    data3.mkdir()
    data3_entry = data3 / "entry.txt"
    data3_entry.write_text("This is data 3.")

    beta1 = tmp_path / "beta1"
    beta1.mkdir()
    beta1_entry = beta1 / "entry.txt"
    beta1_entry.write_text("This is beta 1.")

    beta2 = tmp_path / "beta2"
    beta2.mkdir()
    beta2_entry = beta2 / "entry.txt"
    beta2_entry.write_text("This is beta 2.")


def test_data_tables_as_dictionary(tdt_manager):
    assert "testalpha" in tdt_manager.data_tables
    assert "testdelta" not in tdt_manager.data_tables


def test_to_dict(tdt_manager):
    as_dict = tdt_manager.to_dict()
    assert "testalpha" in as_dict
    assert "testdelta" not in as_dict
    testalpha_as_dict = as_dict["testalpha"]
    assert "columns" in testalpha_as_dict


def test_index(tdt_manager):
    index = tdt_manager.index()
    assert len(index.__root__) >= 1
    entry = index.find_entry("testalpha")
    assert entry
    entry = index.find_entry("testomega")
    assert not entry


def test_reload(tdt_manager, tmp_path):
    assert len(tdt_manager["testalpha"].data) == 2
    loc1 = tmp_path / "testalpha.loc"
    loc1.write_text(LOC_ALPHA_CONTENTS_V2)
    tdt_manager.reload_tables()
    assert len(tdt_manager["testalpha"].data) == 3


def test_reload_by_path(tdt_manager, tmp_path):
    assert len(tdt_manager["testalpha"].data) == 2
    loc1 = tmp_path / "testalpha.loc"
    loc1.write_text(LOC_ALPHA_CONTENTS_V2)
    tdt_manager.reload_tables(path=str(loc1))
    assert len(tdt_manager["testalpha"].data) == 3


def test_reload_by_name(tdt_manager, tmp_path):
    assert len(tdt_manager["testalpha"].data) == 2
    loc1 = tmp_path / "testalpha.loc"
    loc1.write_text(LOC_ALPHA_CONTENTS_V2)
    tdt_manager.reload_tables("testalpha")
    assert len(tdt_manager["testalpha"].data) == 3


def test_merging_tables(merged_tdt_manager):
    assert len(merged_tdt_manager["testbeta"].data) == 2


def test_to_json(merged_tdt_manager, tmp_path):
    json_path = tmp_path / "as_json.json"
    assert not json_path.exists()
    merged_tdt_manager.to_json(json_path)
    assert json_path.exists()
