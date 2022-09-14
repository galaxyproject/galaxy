from galaxy.tool_util.biotools.source import GitContentBiotoolsMetadataSource
from ._util import content_dir


def test_edam_parse_bwa():
    metadata_source = GitContentBiotoolsMetadataSource(content_dir)
    biotools_entry = metadata_source.get_biotools_metadata("bwa")
    assert biotools_entry
    parsed_edam_info = biotools_entry.edam_info
    assert len(parsed_edam_info.edam_operations) == 4
    assert "operation_3198" in parsed_edam_info.edam_operations
    assert len(parsed_edam_info.edam_topics) == 1
    assert "topic_0102" in parsed_edam_info.edam_topics
