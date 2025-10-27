from galaxy.jobs.job_destination import JobDestination


def the_destination(resource_params):
    job_destination = JobDestination(runner="local")
    how_store = resource_params.get("how_store", None)
    # Retrieve answer from user about whether to store on fast or slow disk,
    # translate to object store ID to give to job handling code.
    object_store_id = "dynamic_s3" if how_store == "slow" else "dynamic_ebs"
    job_destination.params["object_store_id"] = object_store_id
    return job_destination
