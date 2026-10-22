"""API test helpers shared by the API and integration test suites."""

from galaxy_test.base.populators import DatasetPopulator


def upload_flat_sample_sheet(dataset_populator: DatasetPopulator) -> None:
    column_definitions = [{"type": "int", "name": "replicate", "optional": False, "default_value": 0}]
    with dataset_populator.test_history(require_new=False) as history_id:
        elements = [
            {
                "src": "url",
                "url": dataset_populator.base64_url_for_string("hello world"),
                "info": "my cool hello world",
                "name": "sample1",
                "row": [42],
            }
        ]
        targets = [
            {
                "destination": {"type": "hdca"},
                "elements": elements,
                "collection_type": "sample_sheet",
                "column_definitions": column_definitions,
            }
        ]
        payload = {
            "history_id": history_id,
            "targets": targets,
        }
        dataset_populator.fetch(payload)
        hdca = assert_one_collection_created_in_history(dataset_populator, history_id)
        assert len(hdca["elements"]) == 1, hdca
        element0 = hdca["elements"][0]
        assert element0["element_identifier"] == "sample1"
        assert element0["columns"][0] == 42
        object0 = element0["object"]
        assert object0["state"] == "ok"
        assert hdca["column_definitions"] is not None


def assert_one_collection_created_in_history(dataset_populator: DatasetPopulator, history_id: str) -> dict:
    contents = dataset_populator.get_history_contents_of_type(history_id, "dataset_collections")
    assert len(contents) == 1
    hdca = contents[0]
    assert hdca["history_content_type"] == "dataset_collection"
    hdca_id = hdca["id"]
    return dataset_populator.get_history_collection_details(history_id, content_id=hdca_id)
