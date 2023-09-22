from galaxy.jobs import JobDestination


def the_destination(resource_params):
    job_destination = JobDestination()
    job_destination.runner = "local"
    how_store = resource_params.get("how_store", None)
    # Retrieve answer from user about whether to store on fast or slow disk,
    # translate to object store ID to give to job handling code.
    object_store_id = "dynamic_ebs"
    if how_store == "slow":
        object_store_id = "dynamic_s3"
    job_destination.params["object_store_id"] = object_store_id
    return job_destination
