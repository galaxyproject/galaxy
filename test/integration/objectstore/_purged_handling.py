import os
import time

from galaxy_test.base.populators import DatasetPopulator


def purge_while_job_running(dataset_populator: DatasetPopulator, sleep_before_purge=4):
    with dataset_populator.test_history() as history_id:
        response = dataset_populator.run_tool(
            "all_output_types",
            inputs={
                "sleep_param": 5,
            },
            history_id=history_id,
        )
        job = dataset_populator.get_job_details(response["jobs"][0]["id"], full=True).json()
        # Sleep a second to make sure we template command before purging output
        time.sleep(sleep_before_purge)
        hda_ids = []
        hda_filenames = []
        for output_name, output in job["outputs"].items():
            if output_name == "static_output_2":
                # We need to keep one output so the job doesn't get cancelled
                continue
            details = dataset_populator.get_history_dataset_details(history_id=history_id, dataset_id=output["id"])
            hda_filenames.append(details["file_name"])
            dataset_populator.delete_dataset(
                history_id=history_id, content_id=output["id"], purge=True, wait_for_purge=True
            )
            hda_ids.append(output["id"])
        for output_collection in job["output_collections"].values():
            hdca = dataset_populator.get_history_collection_details(
                history_id=history_id, content_id=output_collection["id"]
            )
            for element in hdca["elements"]:
                hda_id = element["object"]["id"]
                dataset_populator.delete_dataset(
                    history_id=history_id, content_id=hda_id, purge=True, wait_for_purge=True
                )
                hda_ids.append(hda_id)
        dataset_populator.wait_for_job(job["id"], assert_ok=True)
        # Now make sure we can't find the datasets
        for hda_id in hda_ids:
            exception = None
            try:
                dataset_populator.get_history_dataset_content(history_id=history_id, dataset_id=hda_id)
            except AssertionError as e:
                exception = e
            assert exception and "The dataset you are attempting to view has been purged" in str(exception)
            output_details = dataset_populator.get_history_dataset_details(history_id=history_id, dataset_id=hda_id)
            # Make sure that we don't revert state while finishing job
            assert output_details["purged"]
        for file_name in hda_filenames:
            # Make sure job didn't push to object store
            assert not os.path.exists(file_name), f"Expected {file_name} to be purged."
