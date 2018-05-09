from galaxy.datatypes.registry import example_datatype_registry_for_sample


def test_matches_any():
    datatypes_registry = example_datatype_registry_for_sample()
    data_datatype = datatypes_registry.get_datatype_by_extension('data')
    fasta_datatype = datatypes_registry.get_datatype_by_extension('fasta')
    fastq_datatype = datatypes_registry.get_datatype_by_extension('fastq')
    fastqsanger_datatype = datatypes_registry.get_datatype_by_extension('fastqsanger')
    fastqgz_datatype = datatypes_registry.get_datatype_by_extension('fastq.gz')
    fastqbz2_datatype = datatypes_registry.get_datatype_by_extension('fastq.bz2')
    fastqsangergz_datatype = datatypes_registry.get_datatype_by_extension('fastqsanger.gz')
    fastqsangerbz2_datatype = datatypes_registry.get_datatype_by_extension('fastqsanger.bz2')
    h5_datatype = datatypes_registry.get_datatype_by_extension('h5')
    mz5_datatype = datatypes_registry.get_datatype_by_extension('mz5')

    # Test empty list behavior.
    assert not fasta_datatype.matches_any([])

    # Test direct match with self.
    assert fastq_datatype.matches_any([fastq_datatype])
    assert fastq_datatype.matches_any([fastq_datatype.__class__])

    # Test plain mismatches.
    assert not fasta_datatype.matches_any([fastq_datatype])
    assert not fasta_datatype.matches_any([fastq_datatype.__class__])
    assert not fastq_datatype.matches_any([fasta_datatype])
    assert not fastq_datatype.matches_any([fasta_datatype.__class__])

    # Test simple match behavior of data.
    assert fasta_datatype.matches_any([data_datatype])
    assert not data_datatype.matches_any([fasta_datatype])

    # Test inheritance.
    assert fastqsanger_datatype.matches_any([fastq_datatype])
    assert fastqsanger_datatype.matches_any([fastq_datatype.__class__])

    # Test dynamic subclass handling.
    assert not h5_datatype.matches_any([mz5_datatype])
    assert mz5_datatype.matches_any([h5_datatype])

    # Test compressed datatype handling.
    assert not data_datatype.matches_any([fastqsangergz_datatype])
    assert not fastq_datatype.matches_any([fastqsangergz_datatype])
    assert not fastqsanger_datatype.matches_any([fastqsangergz_datatype])
    assert fastqsangergz_datatype.matches_any([data_datatype])
    assert not fastqsangergz_datatype.matches_any([fastqsanger_datatype])
    assert fastqsangergz_datatype.matches_any([fastqgz_datatype])
    assert not fastqsangerbz2_datatype.matches_any([fastqgz_datatype])
    assert not fastqsangerbz2_datatype.matches_any([fastqsangergz_datatype])
    assert fastqsangerbz2_datatype.matches_any([fastqbz2_datatype])
