import os
from collections.abc import Callable

from galaxy_test.base.populators import (
    DatasetPopulator,
    wait_on,
)


def purge_while_job_running(
    dataset_populator: DatasetPopulator,
    sleep_param: int = 5,
    job_working_directory: Callable[[str], str] | None = None,
):
    """Purge the outputs of a running ``all_output_types`` job.

    With remote tool evaluation the command line is templated inside the running job,
    and templating fails if the outputs are purged first. Pass ``job_working_directory``
    (mapping an encoded job id to its working directory) to wait for that.
    """
    with dataset_populator.test_history() as history_id:
        response = dataset_populator.run_tool(
            "all_output_types",
            inputs={
                "sleep_param": sleep_param,
            },
            history_id=history_id,
        )
        job = dataset_populator.get_job_details(response["jobs"][0]["id"], full=True).json()
        # Make sure job runs (and thus command is templated before purging output)
        dataset_populator.wait_for_job(job["id"], ok_states=["running"])
        if job_working_directory:
            tool_script = os.path.join(job_working_directory(job["id"]), "tool_script.sh")

            def command_templated():
                with open(tool_script) as fh:
                    # galaxy.json is the last argument of the tool's command
                    return "galaxy.json" in fh.read() or None

            wait_on(command_templated, "remote tool evaluation to template the command line")
        hda_ids = []
        hda_filenames = []
        for output_name, output in job["outputs"].items():
            if output_name == "static_output_2":
                # We need to keep one output so the job doesn't get cancelled
                continue
            details = dataset_populator.get_history_dataset_details(
                history_id=history_id, content_id=output["id"], wait=False
            )
            if not output_name.startswith("discovered_output"):
                # We're not precreating discovered outputs on disk
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
                # Technically the static pair elements are already included in job["outputs"],
                # but no harm purging them again here, in case we ever change that logic.
                hda_id = element["object"]["id"]
                dataset_populator.delete_dataset(
                    history_id=history_id, content_id=hda_id, purge=True, wait_for_purge=True
                )
                hda_ids.append(hda_id)
        dataset_populator.wait_for_job(job["id"], assert_ok=True)
        # Now make sure we can't find the datasets on disk
        # We're not covering discovered datasets here, those can't be purged while the job is running.
        for hda_id in hda_ids:
            exception = None
            try:
                dataset_populator.get_history_dataset_content(history_id=history_id, dataset_id=hda_id)
            except AssertionError as e:
                exception = e
            assert exception and "The dataset you are attempting to view has been purged" in str(exception), str(
                exception
            )
            output_details = dataset_populator.get_history_dataset_details(
                history_id=history_id, content_id=hda_id, wait=False
            )
            # Make sure that we don't revert state while finishing job
            assert output_details["purged"], f"expected output '{output_name}' to be purged, but it is not purged."
            assert not output_details.get("file_name")

        for file_name in hda_filenames:
            # Make sure job didn't push to object store
            assert not os.path.exists(file_name), f"Expected {file_name} to be purged."
