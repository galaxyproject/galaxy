def check_example_1(hdca, dataset_populator):
    assert hdca["collection_type"] == "list"
    assert hdca["element_count"] == 2

    first_dce = hdca["elements"][0]
    first_hda = first_dce["object"]
    assert first_hda["hid"] > 3


def check_example_2(hdca, dataset_populator):
    assert hdca["collection_type"] == "list:list"
    assert hdca["element_count"] == 2
    first_collection_level = hdca["elements"][0]
    assert first_collection_level["element_type"] == "dataset_collection"
    second_collection_level = first_collection_level["object"]
    assert second_collection_level["collection_type"] == "list"
    assert second_collection_level["elements"][0]["element_type"] == "hda"


def check_example_3(hdca, dataset_populator):
    assert hdca["collection_type"] == "list"
    assert hdca["element_count"] == 2
    first_element = hdca["elements"][0]
    assert first_element["element_identifier"] == "test0forward"


def check_example_4(hdca, dataset_populator):
    assert hdca["collection_type"] == "list:list"
    assert hdca["element_count"] == 2
    first_collection_level = hdca["elements"][0]
    assert first_collection_level["element_identifier"] == "single", hdca
    assert first_collection_level["element_type"] == "dataset_collection"
    second_collection_level = first_collection_level["object"]
    assert "elements" in second_collection_level, hdca
    assert len(second_collection_level["elements"]) == 1, hdca
    i1_element = second_collection_level["elements"][0]
    assert "object" in i1_element, hdca
    assert "element_identifier" in i1_element
    assert i1_element["element_identifier"] == "i1", hdca
    assert len(i1_element["object"]["tags"]) == 0


def check_example_5(hdca, dataset_populator):
    assert hdca["collection_type"] == "list:list"
    assert hdca["element_count"] == 2
    first_collection_level = hdca["elements"][0]
    assert first_collection_level["element_identifier"] == "single", hdca
    assert first_collection_level["element_type"] == "dataset_collection"
    second_collection_level = first_collection_level["object"]
    assert "elements" in second_collection_level, hdca
    assert len(second_collection_level["elements"]) == 1, hdca
    i1_element = second_collection_level["elements"][0]
    assert "object" in i1_element, hdca
    assert "element_identifier" in i1_element
    assert i1_element["element_identifier"] == "i1", hdca
    tags = i1_element["object"]["tags"]
    assert len(tags) > 0
    assert "group:single" in tags, tags
    assert "i1" in tags, tags


def check_example_6(hdca, dataset_populator):
    assert hdca["collection_type"] == "list"
    assert hdca["element_count"] == 3
    i1_element = hdca["elements"][0]
    assert "object" in i1_element, hdca
    assert "element_identifier" in i1_element
    assert i1_element["element_identifier"] == "i1", hdca
    tags = i1_element["object"]["tags"]
    assert len(tags) == 2
    assert "random" in tags
    assert "group:type:single" in tags


EXAMPLE_1 = {
    "rules": {
        "rules": [
            {
                "type": "add_column_metadata",
                "value": "identifier0",
            }
        ],
        "mapping": [
            {
                "type": "list_identifiers",
                "columns": [0],
            }
        ],
    },
    "test_data": {
        "type": "list",
        "elements": [
            {
                "identifier": "i1",
                "contents": "0",
                "class": "File",
            },
            {
                "identifier": "i2",
                "contents": "1",
                "class": "File",
            },
        ],
    },
    "check": check_example_1,
    "output_hid": 6,
}


EXAMPLE_2 = {
    "rules": {
        "rules": [
            {
                "type": "add_column_metadata",
                "value": "identifier0",
            },
            {
                "type": "add_column_metadata",
                "value": "identifier0",
            },
        ],
        "mapping": [
            {
                "type": "list_identifiers",
                "columns": [0, 1],
            }
        ],
    },
    "test_data": {
        "type": "list",
        "elements": [
            {
                "identifier": "i1",
                "contents": "0",
                "class": "File",
            },
            {
                "identifier": "i2",
                "contents": "1",
                "class": "File",
            },
        ],
    },
    "check": check_example_2,
    "output_hid": 6,
}

# Flatten
EXAMPLE_3 = {
    "rules": {
        "rules": [
            {
                "type": "add_column_metadata",
                "value": "identifier0",
            },
            {
                "type": "add_column_metadata",
                "value": "identifier1",
            },
            {
                "type": "add_column_concatenate",
                "target_column_0": 0,
                "target_column_1": 1,
            },
        ],
        "mapping": [
            {
                "type": "list_identifiers",
                "columns": [2],
            }
        ],
    },
    "test_data": {
        "type": "list:paired",
        "elements": [
            {
                "identifier": "test0",
                "elements": [
                    {"identifier": "forward", "class": "File", "contents": "TestData123"},
                    {"identifier": "reverse", "class": "File", "contents": "TestData123"},
                ],
            }
        ],
    },
    "check": check_example_3,
    "output_hid": 6,
}

# Nesting with group tags.
EXAMPLE_4 = {
    "rules": {
        "rules": [
            {
                "type": "add_column_metadata",
                "value": "identifier0",
            },
            {"type": "add_column_group_tag_value", "value": "type", "default_value": "unused"},
        ],
        "mapping": [
            {
                "type": "list_identifiers",
                "columns": [1, 0],
            }
        ],
    },
    "test_data": {
        "type": "list",
        "elements": [
            {"identifier": "i1", "contents": "0", "class": "File", "tags": ["random", "group:type:single"]},
            {"identifier": "i2", "contents": "1", "class": "File", "tags": ["random", "group:type:paired"]},
            {"identifier": "i3", "contents": "2", "class": "File", "tags": ["random", "group:type:paired"]},
        ],
    },
    "check": check_example_4,
    "output_hid": 8,
}


EXAMPLE_5 = {
    "rules": {
        "rules": [
            {
                "type": "add_column_metadata",
                "value": "identifier0",
            },
            {"type": "add_column_group_tag_value", "value": "type", "default_value": "unused"},
        ],
        "mapping": [
            {
                "type": "list_identifiers",
                "columns": [1, 0],
            },
            {
                "type": "group_tags",
                "columns": [1],
            },
            {
                "type": "tags",
                "columns": [0],
            },
        ],
    },
    "test_data": {
        "type": "list",
        "elements": [
            {"identifier": "i1", "contents": "0", "class": "File", "tags": ["random", "group:type:single"]},
            {"identifier": "i2", "contents": "1", "class": "File", "tags": ["random", "group:type:paired"]},
            {"identifier": "i3", "contents": "2", "class": "File", "tags": ["random", "group:type:paired"]},
        ],
    },
    "check": check_example_5,
    "output_hid": 8,
}


EXAMPLE_6 = {
    "rules": {
        "rules": [
            {
                "type": "add_column_metadata",
                "value": "identifier0",
            },
            {
                "type": "add_column_metadata",
                "value": "tags",
            },
        ],
        "mapping": [
            {
                "type": "list_identifiers",
                "columns": [0],
            },
            {
                "type": "tags",
                "columns": [1],
            },
        ],
    },
    "test_data": {
        "type": "list",
        "elements": [
            {"identifier": "i1", "contents": "0", "class": "File", "tags": ["random", "group:type:single"]},
            {"identifier": "i2", "contents": "1", "class": "File", "tags": ["random", "group:type:paired"]},
            {"identifier": "i3", "contents": "2", "class": "File", "tags": ["random", "group:type:paired"]},
        ],
    },
    "check": check_example_6,
    "output_hid": 8,
}


def check_example_flatten_with_indices(hdca, dataset_populator):
    assert hdca["collection_type"] == "list"
    assert hdca["element_count"] == 2
    first_element = hdca["elements"][0]
    assert first_element["element_identifier"] == "0_0", hdca
    second_element = hdca["elements"][1]
    assert second_element["element_identifier"] == "0_1", hdca


EXAMPLE_FLATTEN_USING_INDICES = {
    "rules": {
        "rules": [
            {
                "type": "add_column_metadata",
                "value": "index0",
            },
            {
                "type": "add_column_value",
                "value": "_",
            },
            {
                "type": "add_column_metadata",
                "value": "index1",
            },
            {
                "type": "add_column_concatenate",
                "target_column_0": 0,
                "target_column_1": 1,
            },
            {
                "type": "add_column_concatenate",
                "target_column_0": 3,
                "target_column_1": 2,
            },
        ],
        "mapping": [
            {
                "type": "list_identifiers",
                "columns": [4],
            }
        ],
    },
    "test_data": {
        "type": "list:paired",
        "elements": [
            {
                "identifier": "test0",
                "elements": [
                    {"identifier": "forward", "class": "File", "contents": "TestData123forward"},
                    {"identifier": "reverse", "class": "File", "contents": "TestData123reverse"},
                ],
            },
        ],
    },
    "check": check_example_flatten_with_indices,
    "output_hid": 6,
}


def check_example_create_paired_or_unpaired_with_unmatched_forward_becoming_unpaired(hdca, dataset_populator):
    assert hdca["collection_type"] == "list:paired_or_unpaired"
    assert hdca["element_count"] == 4
    sample1_el = hdca["elements"][0]
    assert "object" in sample1_el, hdca
    assert "element_identifier" in sample1_el
    assert sample1_el["element_identifier"] == "sample1", hdca
    child_collection_level = sample1_el["object"]
    assert child_collection_level["collection_type"] == "paired_or_unpaired"
    assert child_collection_level["elements"][0]["element_identifier"] == "forward", hdca

    sample2_el = hdca["elements"][1]
    assert "object" in sample2_el, hdca
    assert "element_identifier" in sample2_el
    assert sample2_el["element_identifier"] == "sample2", hdca
    child_collection_level = sample2_el["object"]
    assert child_collection_level["collection_type"] == "paired_or_unpaired"
    assert child_collection_level["elements"][0]["element_identifier"] == "unpaired", hdca

    sample3_el = hdca["elements"][2]
    assert "object" in sample3_el, hdca
    assert "element_identifier" in sample3_el
    assert sample3_el["element_identifier"] == "sample3", hdca
    child_collection_level = sample3_el["object"]
    assert child_collection_level["collection_type"] == "paired_or_unpaired"
    assert child_collection_level["elements"][0]["element_identifier"] == "unpaired", hdca

    sample4_el = hdca["elements"][2]
    assert "object" in sample4_el, hdca
    assert "element_identifier" in sample4_el
    assert sample4_el["element_identifier"] == "sample3", hdca
    child_collection_level = sample4_el["object"]
    assert child_collection_level["collection_type"] == "paired_or_unpaired"
    assert child_collection_level["elements"][0]["element_identifier"] == "unpaired", hdca


EXAMPLE_CREATE_PAIRED_OR_UNPAIRED_COLLECTION = {
    "rules": {
        "rules": [
            {
                "type": "add_column_metadata",
                "value": "identifier0",
            },
            {
                "type": "add_column_metadata",
                "value": "identifier1",
            },
        ],
        "mapping": [
            {
                "type": "list_identifiers",
                "columns": [0],
            },
            {
                "type": "paired_or_unpaired_identifier",
                "columns": [1],
            },
        ],
    },
    "test_data": {
        "type": "list:list",
        "elements": [
            {
                "identifier": "sample1",
                "elements": [
                    {"identifier": "forward", "class": "File", "contents": "TestData123forward"},
                    {"identifier": "reverse", "class": "File", "contents": "TestData123reverse"},
                ],
            },
            {
                "identifier": "sample2",
                "elements": [
                    {"identifier": "unpaired", "class": "File", "contents": "TestData123unpaired"},
                ],
            },
            {
                "identifier": "sample3",
                "elements": [
                    {"identifier": "u", "class": "File", "contents": "TestData123unpaired-2"},
                ],
            },
            {
                "identifier": "sample4",
                "elements": [
                    {"identifier": "forward", "class": "File", "contents": "TestData123unpaired-3"},
                ],
            },
        ],
    },
    "check": check_example_create_paired_or_unpaired_with_unmatched_forward_becoming_unpaired,
    "output_hid": 12,
}


def check_example_flatten_paired_or_unpaired(hdca, dataset_populator):
    assert hdca["collection_type"] == "list"
    assert hdca["element_count"] == 3
    first_element = hdca["elements"][0]
    assert first_element["element_identifier"] == "test0forward", hdca
    second_element = hdca["elements"][1]
    assert second_element["element_identifier"] == "test0reverse", hdca
    third_element = hdca["elements"][2]
    assert third_element["element_identifier"] == "test1unpaired", hdca


EXAMPLE_FLATTEN_PAIRED_OR_UNPAIRED = {
    "rules": {
        "rules": [
            {
                "type": "add_column_metadata",
                "value": "identifier0",
            },
            {
                "type": "add_column_metadata",
                "value": "identifier1",
            },
            {
                "type": "add_column_concatenate",
                "target_column_0": 0,
                "target_column_1": 1,
            },
        ],
        "mapping": [
            {
                "type": "list_identifiers",
                "columns": [2],
            }
        ],
    },
    "test_data": {
        "type": "list:paired_or_unpaired",
        "elements": [
            {
                "identifier": "test0",
                "elements": [
                    {"identifier": "forward", "class": "File", "contents": "TestData123forward"},
                    {"identifier": "reverse", "class": "File", "contents": "TestData123reverse"},
                ],
            },
            {
                "identifier": "test1",
                "elements": [
                    {"identifier": "unpaired", "class": "File", "contents": "TestData123unpaired"},
                ],
            },
        ],
    },
    "check": check_example_flatten_paired_or_unpaired,
    "output_hid": 8,
}


def check_example_sample_sheet_simple_to_nested_list(hdca, dataset_populator):
    assert hdca["collection_type"] == "list:list"
    assert hdca["element_count"] == 2
    treat1_el = hdca["elements"][0]
    assert "object" in treat1_el, hdca
    assert "element_identifier" in treat1_el
    assert treat1_el["element_identifier"] == "treat1", hdca

    treat2_el = hdca["elements"][1]
    assert "object" in treat2_el, hdca
    assert "element_identifier" in treat2_el
    assert treat2_el["element_identifier"] == "treat2", hdca


EXAMPLE_SAMPLE_SHEET_SIMPLE_TO_NESTED_LIST = {
    "rules": {
        "rules": [
            {
                "type": "add_column_from_sample_sheet_index",
                "value": 0,
            },
            {
                "type": "add_column_metadata",
                "value": "identifier0",
            },
        ],
        "mapping": [
            {
                "type": "list_identifiers",
                "columns": [0, 1],
            },
        ],
    },
    "test_data": {
        "type": "sample_sheet",
        "elements": [
            {"identifier": "i1", "contents": "0", "class": "File"},
            {"identifier": "i2", "contents": "1", "class": "File"},
            {"identifier": "i3", "contents": "2", "class": "File"},
        ],
        "rows": {
            "i1": ["treat1"],
            "i2": ["treat2"],
            "i3": ["treat1"],
        },
    },
    "check": check_example_sample_sheet_simple_to_nested_list,
    "output_hid": 8,
}


def check_example_sample_sheet_simple_to_nested_list_of_pairs(hdca, dataset_populator):
    assert hdca["collection_type"] == "list:list:paired"
    assert hdca["element_count"] == 2
    treat1_el = hdca["elements"][0]
    assert "object" in treat1_el, hdca
    assert "element_identifier" in treat1_el
    assert treat1_el["element_identifier"] == "treat1", hdca

    treat1list = treat1_el["object"]
    assert "elements" in treat1list, hdca
    assert len(treat1list["elements"]) == 2, hdca

    treat2_el = hdca["elements"][1]
    assert "object" in treat2_el, hdca
    assert "element_identifier" in treat2_el
    assert treat2_el["element_identifier"] == "treat2", hdca

    treat2list = treat2_el["object"]
    assert "elements" in treat2list, hdca
    assert len(treat2list["elements"]) == 1, hdca


EXAMPLE_SAMPLE_SHEET_SIMPLE_TO_NESTED_LIST_OF_PAIRS = {
    "rules": {
        "rules": [
            {
                "type": "add_column_from_sample_sheet_index",
                "value": 0,
            },
            {
                "type": "add_column_metadata",
                "value": "identifier0",
            },
            {
                "type": "add_column_metadata",
                "value": "identifier1",
            },
        ],
        "mapping": [
            {
                "type": "list_identifiers",
                "columns": [0, 1],
            },
            {
                "type": "paired_identifier",
                "columns": [2],
            },
        ],
    },
    "test_data": {
        "type": "sample_sheet:paired",
        "elements": [
            {
                "identifier": "i1",
                "elements": [
                    {"identifier": "forward", "class": "File", "contents": "i1forwardcontents"},
                    {"identifier": "reverse", "class": "File", "contents": "i1reversecontents"},
                ],
            },
            {
                "identifier": "i2",
                "elements": [
                    {"identifier": "forward", "class": "File", "contents": "i2forwardcontents"},
                    {"identifier": "reverse", "class": "File", "contents": "i2reversecontents"},
                ],
            },
            {
                "identifier": "i3",
                "elements": [
                    {"identifier": "forward", "class": "File", "contents": "i3forwardcontents"},
                    {"identifier": "reverse", "class": "File", "contents": "i3reversecontents"},
                ],
            },
        ],
        "rows": {
            "i1": ["treat1"],
            "i2": ["treat2"],
            "i3": ["treat1"],
        },
    },
    "check": check_example_sample_sheet_simple_to_nested_list_of_pairs,
    "output_hid": 14,
}
