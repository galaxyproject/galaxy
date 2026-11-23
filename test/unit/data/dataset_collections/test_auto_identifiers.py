from galaxy.model.dataset_collections.auto_identifiers import (
    fill_in_identifiers,
    FillIdentifiers,
    guess_filename_from_url,
)


def test_fill_in_identifiers_simple():
    uris = {
        "https://ftp.sra.ebi.ac.uk/vol1/fastq/DRR000/DRR000770/DRR000770.fastq.gz": None,
        "https://ftp.sra.ebi.ac.uk/vol1/fastq/DRR000/DRR000771/DRR000771.fastq.gz": None,
    }
    new_map = run_fill_on_dict(uris)
    assert new_map["https://ftp.sra.ebi.ac.uk/vol1/fastq/DRR000/DRR000770/DRR000770.fastq.gz"] == "DRR000770"
    assert new_map["https://ftp.sra.ebi.ac.uk/vol1/fastq/DRR000/DRR000771/DRR000771.fastq.gz"] == "DRR000771"


def test_fill_in_identifiers_retains_existing_maps():
    uris = {
        "https://ftp.sra.ebi.ac.uk/vol1/fastq/DRR000/DRR000770/DRR000770.fastq.gz": "abc",
        "https://ftp.sra.ebi.ac.uk/vol1/fastq/DRR000/DRR000771/DRR000771.fastq.gz": None,
    }
    new_map = run_fill_on_dict(uris)
    assert new_map["https://ftp.sra.ebi.ac.uk/vol1/fastq/DRR000/DRR000770/DRR000770.fastq.gz"] == "abc"
    assert new_map["https://ftp.sra.ebi.ac.uk/vol1/fastq/DRR000/DRR000771/DRR000771.fastq.gz"] == "DRR000771"


def test_fill_in_identifiers_avoids_duplicates():
    uris = {
        "https://ftp.sra.ebi.ac.uk/vol1/fastq/DRR000/DRR000770/DRR000770.fastq.gz": None,
        "https://ftp.sra.ebi.ac.uk/vol1/fastq/DRR000/DRR000771/DRR000770.fastq.gz": None,
    }
    new_map = run_fill_on_dict(uris)
    assert new_map["https://ftp.sra.ebi.ac.uk/vol1/fastq/DRR000/DRR000770/DRR000770.fastq.gz"] == "DRR000770"
    assert new_map["https://ftp.sra.ebi.ac.uk/vol1/fastq/DRR000/DRR000771/DRR000770.fastq.gz"] == "DRR000770_1"


def run_fill_on_dict(uris):
    config = FillIdentifiers(fill_inner_list_identifiers=True)
    as_tuples = list(uris.items())
    new_ids = fill_in_identifiers(as_tuples, config)
    new_uris = {}
    for uri, identifier in zip(uris.keys(), new_ids):
        new_uris[uri] = identifier
    return new_uris


def test_guess_filename_from_url_leaves_out_nested_userinfo():
    assert guess_filename_from_url("https://example.org/ftp://user:secret@inner") == "inner"
    assert guess_filename_from_url("https://example.org/ftp://user:secret@inner/a.bed") == "a.bed"


def test_guess_filename_from_url_leaves_out_userinfo_of_pathless_url():
    assert "secret" not in guess_filename_from_url("https://user:secret@example.org")


def test_fill_in_identifiers_leaves_out_nested_userinfo():
    uri = "https://example.org/ftp://user:secret@inner.fastq.gz"
    new_map = run_fill_on_dict({uri: None})
    assert new_map[uri] == "inner"
