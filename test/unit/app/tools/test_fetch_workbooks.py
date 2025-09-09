import base64
import os

import pytest

from galaxy.exceptions import RequestParameterInvalidException
from galaxy.model.dataset_collections.auto_identifiers import FillIdentifiers
from galaxy.model.dataset_collections.rule_target_columns import column_titles_to_headers
from galaxy.model.dataset_collections.rule_target_models import target_models
from galaxy.model.dataset_collections.workbook_util import read_column_header_titles
from galaxy.tools.fetch.workbooks import (
    _infer_fetch_workbook_collection_type,
    _validate_parsed_column_headers,
    DEFAULT_WORKBOOK_TITLE,
    EXCEPTION_NO_URIS_FOUND,
    EXCEPTION_TOO_MANY_URI_COLUMNS,
    generate,
    GenerateFetchWorkbookRequest,
    parse,
    ParsedFetchWorkbook,
    ParseFetchWorkbook,
)
from galaxy.util.resources import resource_path

WRITE_TEST_WORKBOOKS = False


def test_fetch_datasets_workbook():
    request = GenerateFetchWorkbookRequest()
    workbook = generate(request)
    assert workbook
    worksheet = workbook.active
    assert worksheet.title == DEFAULT_WORKBOOK_TITLE
    assert worksheet.cell(1, 1).value == "URI"

    header_titles = read_column_header_titles(worksheet)
    assert header_titles == ["URI", "Name"]

    if WRITE_TEST_WORKBOOKS:
        path = "~/fetch_workbook.xlsx"
        expanded_path = os.path.expanduser(path)
        workbook.save(expanded_path)


def test_fetch_list_workbook():
    request = GenerateFetchWorkbookRequest(
        type="collection",
        collection_type="list",
    )
    workbook = generate(request)
    assert workbook
    worksheet = workbook.active

    header_titles = read_column_header_titles(worksheet)
    assert header_titles == ["URI", "List Identifier"]


def test_fetch_multiple_lists_workbook():
    request = GenerateFetchWorkbookRequest(
        type="collections",
        collection_type="list",
    )
    workbook = generate(request)
    assert workbook
    worksheet = workbook.active

    header_titles = read_column_header_titles(worksheet)
    assert header_titles == ["URI", "List Identifier", "Collection Name"]


def test_fetch_list_paired_workbook():
    request = GenerateFetchWorkbookRequest(
        type="collection",
        collection_type="list:paired",
    )
    workbook = generate(request)
    assert workbook
    worksheet = workbook.active

    header_titles = read_column_header_titles(worksheet)
    assert header_titles == ["URI 1 (Forward)", "URI 2 (Reverse)", "List Identifier"]

    if WRITE_TEST_WORKBOOKS:
        path = "~/fetch_workbook_paired.xlsx"
        expanded_path = os.path.expanduser(path)
        workbook.save(expanded_path)


def test_fetch_list_paired_or_unpaired_workbook():
    request = GenerateFetchWorkbookRequest(
        type="collection",
        collection_type="list:paired_or_unpaired",
    )
    workbook = generate(request)
    assert workbook
    worksheet = workbook.active

    header_titles = read_column_header_titles(worksheet)
    assert header_titles == ["URI 1 (Forward)", "URI 2 (Optional/Reverse)", "List Identifier"]


def test_parse_datasets():
    content = unittest_file_to_base64("fetch_workbook.xlsx")
    parse_request = ParseFetchWorkbook(
        content=content,
    )
    parsed = parse(parse_request)
    assert_is_simple_example_parsed(parsed)


def assert_is_simple_example_parsed(parsed: ParsedFetchWorkbook):
    assert len(parsed.rows) == 1
    row0 = parsed.rows[0]
    assert row0["url"] == "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/4.bed"
    assert row0["name"] == "4.bed"

    assert len(parsed.columns) == 2


def test_parse_datasets_csv():
    content = unittest_file_to_base64("fetch_workbook.csv")
    parse_request = ParseFetchWorkbook(
        content=content,
    )
    parsed = parse(parse_request)
    assert_is_simple_example_parsed(parsed)


def test_parse_datasets_tsv():
    content = unittest_file_to_base64("fetch_workbook.tsv")
    parse_request = ParseFetchWorkbook(
        content=content,
    )
    parsed = parse(parse_request)
    assert_is_simple_example_parsed(parsed)


def test_parse_paired_list():
    # workbook has URI 1 and URI 2 columns - make sure they are broken out and have a paired_indicator column
    # for the rule builder.
    content = unittest_file_to_base64("fetch_workbook_paired.xlsx")
    parse_request = ParseFetchWorkbook(
        content=content,
    )
    parsed = parse(parse_request)
    assert len(parsed.rows) == 2
    row0 = parsed.rows[0]
    assert row0["url"] == "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/1.bed"
    assert row0["list_identifiers"] == "sample1"
    assert row0["paired_identifier"] == "1"

    row1 = parsed.rows[1]
    assert row1["url"] == "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/4.bed"
    assert row1["list_identifiers"] == "sample1"
    assert row1["paired_identifier"] == "2"

    assert len(parsed.columns) == 3


def test_parsed_paired_with_hashes():
    content = unittest_file_to_base64("fetch_workbook_paired_with_hashes.xlsx")
    parse_request = ParseFetchWorkbook(
        content=content,
    )
    parsed = parse(parse_request)
    assert len(parsed.rows) == 2

    row0 = parsed.rows[0]
    assert row0["url"] == "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/4.bed"
    assert row0["list_identifiers"] == "sample1"
    assert row0["paired_identifier"] == "1"
    assert row0["list_identifiers"] == "sample1"
    assert row0["hash_md5"] == "37b59762b59fff860460522d271bc111"
    assert (
        row0["hash_sha512"]
        == "b83327251deae7e8c865948573d325a6657eaef10b274ba98d8ba6835f073f787c5621a4a9afd6db894f87bbd4299770f062369a3a39dea8b0263860559ff939"
    )

    row1 = parsed.rows[1]
    assert row1["url"] == "https://raw.githubusercontent.com/galaxyproject/galaxy/dev/test-data/1.bed"
    assert row1["list_identifiers"] == "sample1"
    assert row1["paired_identifier"] == "2"
    assert row1["hash_md5"] == "29e9dd693af0a946e67cd1861b987d13"
    assert (
        row1["hash_sha512"]
        == "9be59f9dc30bc2b35016dc45f5726a249baef2cdee2eb840665d3cdf4d0a0539c50eea1aa96bfd84f3a619782fc9321e5817e005a8a30c318d45c6759c9601bd"
    )


def test_parsed_list_with_auto_identifiers():
    content = unittest_file_to_base64("fetch_workbook_list_without_ids_example.xlsx")
    parse_request = ParseFetchWorkbook(
        content=content, fill_identifiers=FillIdentifiers(fill_inner_list_identifiers=True)
    )
    parsed = parse(parse_request)
    assert len(parsed.rows) == 2
    row0 = parsed.rows[0]
    assert row0["url"] == "https://ftp.sra.ebi.ac.uk/vol1/fastq/DRR000/DRR000770/DRR000770.fastq.gz"
    assert row0["list_identifiers"] == "DRR000770"
    row1 = parsed.rows[1]
    assert row1["url"] == "https://ftp.sra.ebi.ac.uk/vol1/fastq/DRR000/DRR000771/DRR000771.fastq.gz"
    assert row1["list_identifiers"] == "DRR000771"


def test_parsed_list_of_pairs_with_auto_identifiers():
    content = unittest_file_to_base64("fetch_workbook_list_pairs_without_ids_example.xlsx")
    parse_request = ParseFetchWorkbook(
        content=content, fill_identifiers=FillIdentifiers(fill_inner_list_identifiers=True)
    )
    parsed = parse(parse_request)
    assert len(parsed.rows) == 4
    row0 = parsed.rows[0]
    assert row0["url"] == "https://ftp.sra.ebi.ac.uk/vol1/fastq/DRR039/DRR039919/DRR039919_1.fastq.gz"
    assert row0["list_identifiers"] == "DRR039919"


def test_read_column_headers_from_titles():
    # datasets...
    column_headers = column_titles_to_headers(["URI", "Name", "Genome"])[0]
    assert len(column_headers) == 3
    assert column_headers[0].type == "url"
    assert column_headers[0].title == "URI"
    assert column_headers[1].type == "name"
    assert column_headers[1].title == "Name"
    assert column_headers[2].type == "dbkey"
    assert column_headers[2].title == "Genome"

    # simple list...
    column_headers = column_titles_to_headers(["URI", "List Identifier"])[0]
    assert len(column_headers) == 2
    assert column_headers[0].type == "url"
    assert column_headers[0].title == "URI"
    assert column_headers[1].type == "list_identifiers"
    assert column_headers[1].title == "List Identifier"

    # paired list with list two URIs per row....
    column_headers = column_titles_to_headers(["URI 1 (Forward)", "URI 2 (Reverse)", "List Identifier"])[0]
    assert len(column_headers) == 3
    assert column_headers[0].type == "url"
    assert column_headers[0].title == "URI 1 (Forward)"
    assert column_headers[0].type_index == 0

    assert column_headers[1].type == "url"
    assert column_headers[1].title == "URI 2 (Reverse)"
    assert column_headers[1].type_index == 1

    assert column_headers[2].type == "list_identifiers"
    assert column_headers[2].title == "List Identifier"

    # paired list with paired identifier as a row...
    column_headers = column_titles_to_headers(["URI", "List Identifier", "Paired Identifier"])[0]
    assert len(column_headers) == 3
    assert column_headers[0].type == "url"
    assert column_headers[0].title == "URI"
    assert column_headers[0].type_index == 0

    assert column_headers[2].type == "paired_identifier"
    assert column_headers[2].title == "Paired Identifier"
    assert column_headers[2].type_index == 0

    # nested list
    column_headers = column_titles_to_headers(["URI", "Outer List Identifier", "Inner List Identifier"])[0]

    assert len(column_headers) == 3
    assert column_headers[0].type == "url"
    assert column_headers[0].title == "URI"
    assert column_headers[0].type_index == 0

    assert column_headers[1].type == "list_identifiers"
    assert column_headers[1].title == "Outer List Identifier"
    assert column_headers[1].type_index == 0

    assert column_headers[2].type == "list_identifiers"
    assert column_headers[2].title == "Inner List Identifier"
    assert column_headers[2].type_index == 1


def test_infer_fetch_workbook_collection_type():
    column_headers = column_titles_to_headers(["URI", "List Identifier", "Genome"])[0]
    collection_type = _infer_fetch_workbook_collection_type(column_headers)[0]
    assert collection_type == "list"

    column_headers = column_titles_to_headers(["URI", "List Identifier 1", "List Identifier 2", "Genome"])[0]
    collection_type = _infer_fetch_workbook_collection_type(column_headers)[0]
    assert collection_type == "list:list"

    column_headers = column_titles_to_headers(["URI", "List Identifier", "Paired Identifier", "Genome"])[0]
    collection_type = _infer_fetch_workbook_collection_type(column_headers)[0]
    assert collection_type == "list:paired"

    # probably more usable - two URI style list:paired
    column_headers = column_titles_to_headers(["URI 1", "URI 2", "List Identifier", "Genome"])[0]
    collection_type = _infer_fetch_workbook_collection_type(column_headers)[0]
    assert collection_type == "list:paired"

    column_headers = column_titles_to_headers(
        ["URI", "List Identifier 1", "List Identifier 2", "Paired Identifier", "Genome"]
    )[0]
    collection_type = _infer_fetch_workbook_collection_type(column_headers)[0]
    assert collection_type == "list:list:paired"

    column_headers = column_titles_to_headers(["URI 1", "URI 2", "List Identifier 1", "List Identifier 2", "Genome"])[0]
    collection_type = _infer_fetch_workbook_collection_type(column_headers)[0]
    assert collection_type == "list:list:paired"

    # paired/unpaired sheets
    column_headers = column_titles_to_headers(["URI 1", "URI 2 (Optional)", "List Identifier", "Genome"])[0]
    collection_type = _infer_fetch_workbook_collection_type(column_headers)[0]
    assert collection_type == "list:paired_or_unpaired"

    # paired/unpaired sheets
    column_headers = column_titles_to_headers(["URI", "List Identifier", "Paired Identifier (Optional)", "Genome"])[0]
    collection_type = _infer_fetch_workbook_collection_type(column_headers)[0]
    assert collection_type == "list:paired_or_unpaired"


def test_column_target_model_parsing():
    target_models()


def test_validate_parsed_column_headers():
    headers = column_titles_to_headers(["URI 1", "URI 2", "URI 3"])[0]
    with pytest.raises(RequestParameterInvalidException) as exception_info:
        _validate_parsed_column_headers(headers)
    assert EXCEPTION_TOO_MANY_URI_COLUMNS in str(exception_info.value)

    headers = column_titles_to_headers(["Name", "Paired Indicator"])[0]
    with pytest.raises(RequestParameterInvalidException) as exception_info:
        _validate_parsed_column_headers(headers)
    assert EXCEPTION_NO_URIS_FOUND in str(exception_info.value)


def unittest_file_to_base64(filename: str) -> str:
    path = resource_path("galaxy.app_unittest_utils", filename)
    example_as_bytes = path.read_bytes()
    content_base64 = base64.b64encode(example_as_bytes).decode("utf-8")
    return content_base64
