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
