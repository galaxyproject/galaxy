from galaxy.tool_util.biotools.source import (
    ApiBiotoolsMetadataSource,
    BiotoolsMetadataSourceConfig,
    get_biotools_metadata_source,
    GitContentBiotoolsMetadataSource,
)
from ._util import content_dir


def test_git_content():
    metadata_source = GitContentBiotoolsMetadataSource(content_dir)
    bwa_entry = metadata_source.get_biotools_metadata("bwa")
    assert bwa_entry is not None
    assert len(bwa_entry.function) == 6

    missing_entry = metadata_source.get_biotools_metadata("johnscoolbowtie")
    assert missing_entry is None


def test_api_content():
    metadata_source = ApiBiotoolsMetadataSource()
    bwa_entry = metadata_source.get_biotools_metadata("bwa")
    assert bwa_entry is not None
    assert len(bwa_entry.function) >= 6

    missing_entry = metadata_source.get_biotools_metadata("johnscoolbowtie")
    assert missing_entry is None


def test_cascade_content():
    config = BiotoolsMetadataSourceConfig()
    config.content_directory = content_dir
    metadata_source = get_biotools_metadata_source(config)
    bwa_entry = metadata_source.get_biotools_metadata("bwa")
    assert bwa_entry is not None
    assert len(bwa_entry.function) == 6

    # by default API isn't used so bowtie2 empty...
    bowtie2 = metadata_source.get_biotools_metadata("bowtie2")
    assert bowtie2 is None

    # but can be enabled with API
    config = BiotoolsMetadataSourceConfig()
    config.content_directory = content_dir
    config.use_api = True
    metadata_source = get_biotools_metadata_source(config)
    bowtie2 = metadata_source.get_biotools_metadata("bowtie2")
    assert bowtie2 is not None
    assert len(bowtie2.topic) == 3
