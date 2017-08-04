"""Client-centric CWL-related utilities.

Used to share code between the Galaxy test framework
and other Galaxy CWL clients (e.g. Planemo)."""
import hashlib
import json
import os

from collections import namedtuple

from six import iteritems, StringIO


def output_properties(path=None, content=None):
    checksum = hashlib.sha1()
    properties = {
        "class": "File",
    }
    if path is not None:
        properties["path"] = path
        f = open(path, "rb")
    else:
        f = StringIO(content)

    try:
        contents = f.read(1024 * 1024)
        filesize = 0
        while contents != "":
            checksum.update(contents)
            filesize += len(contents)
            contents = f.read(1024 * 1024)
    finally:
        f.close()
    properties["checksum"] = "sha1$%s" % checksum.hexdigest()
    properties["size"] = filesize
    return properties


def galactic_job_json(job, test_data_directory, upload_func, collection_create_func):
    """Adapt a CWL job object to the Galaxy API.

    CWL derived tools in Galaxy can consume a job description sort of like
    CWL job objects via the API but paths need to be replaced with datasets
    and records and arrays with collection references. This function will
    stage files and modify the job description to adapt to these changes
    for Galaxy.
    """

    datasets = []
    dataset_collections = []

    def upload_file(file_path):
        if not os.path.isabs(file_path):
            file_path = os.path.join(test_data_directory, file_path)
        _ensure_file_exists(file_path)
        upload_response = upload_func(FileUploadTarget(file_path))
        dataset = upload_response["outputs"][0]
        datasets.append((dataset, file_path))
        dataset_id = dataset["id"]
        return {"src": "hda", "id": dataset_id}

    def upload_object(the_object):
        upload_response = upload_func(ObjectUploadTarget(the_object))
        dataset = upload_response["outputs"][0]
        datasets.append((dataset, the_object))
        dataset_id = dataset["id"]
        return {"src": "hda", "id": dataset_id}

    def replacement_item(value, force_to_file=False):
        is_dict = isinstance(value, dict)
        is_file = is_dict and value.get("class", None) == "File"

        if force_to_file:
            if is_file:
                return replacement_file(value)
            else:
                return upload_object(value)

        if isinstance(value, list):
            return replacement_list(value)
        elif not isinstance(value, dict):
            return upload_object(value)

        if is_file:
            return replacement_file(value)
        else:
            return replacement_record(value)

    def replacement_file(value):
        file_path = value.get("location", None) or value.get("path", None)
        if file_path is None:
            return value

        return upload_file(file_path)

    def replacement_list(value):
        collection_element_identifiers = []
        for i, item in enumerate(value):
            dataset = replacement_item(item, force_to_file=True)
            collection_element = dataset.copy()
            collection_element["name"] = str(i)
            collection_element_identifiers.append(collection_element)

        collection = collection_create_func(collection_element_identifiers, "list")
        dataset_collections.append(collection)
        hdca_id = collection["id"]
        return {"src": "hdca", "id": hdca_id}

    def replacement_record(value):
        collection_element_identifiers = []
        for record_key, record_value in value.items():
            if record_value.get("class") != "File":
                dataset = replacement_item(record_value, force_to_file=True)
                collection_element = dataset.copy()
            else:
                dataset = upload_file(record_value["location"])
                collection_element = dataset.copy()

            collection_element["name"] = record_key
            collection_element_identifiers.append(collection_element)

        collection = collection_create_func(collection_element_identifiers, "record")
        dataset_collections.append(collection)
        hdca_id = collection["id"]
        return {"src": "hdca", "id": hdca_id}

    replace_keys = {}
    for key, value in iteritems(job):
        replace_keys[key] = replacement_item(value)

    job.update(replace_keys)
    return job, datasets


def _ensure_file_exists(file_path):
    if not os.path.exists(file_path):
        template = "File [%s] does not exist - parent directory [%s] does %sexist, cwd is [%s]"
        parent_directory = os.path.dirname(file_path)
        message = template % (
            file_path,
            parent_directory,
            "" if os.path.exists(parent_directory) else "not ",
            os.getcwd(),
        )
        raise Exception(message)


class FileUploadTarget(object):

    def __init__(self, path):
        self.path = path


class ObjectUploadTarget(object):

    def __init__(self, the_object):
        self.object = the_object


GalaxyOutput = namedtuple("GalaxyOutput", ["history_id", "history_content_type", "history_content_id"])


def output_to_cwl_json(galaxy_output, get_metadata, get_dataset):
    """Convert objects in a Galaxy history into a CWL object.

    Useful in running conformance tests and implementing the cwl-runner
    interface via Galaxy.
    """
    def element_to_cwl_json(element):
        element_output = GalaxyOutput(
            galaxy_output.history_id,
            element["object"]["history_content_type"],
            element["object"]["id"],
        )
        return output_to_cwl_json(element_output, get_metadata, get_dataset)

    output_metadata = get_metadata(galaxy_output.history_content_type, galaxy_output.history_content_id)
    if output_metadata["history_content_type"] == "dataset":
        ext = output_metadata["file_ext"]
        assert output_metadata["state"] == "ok"
        dataset_dict = get_dataset(output_metadata)
        if ext == "expression.json":
            if "content" in dataset_dict:
                return json.loads(dataset_dict["content"])
            else:
                with open(dataset_dict["path"]) as f:
                    return json.load(f)
        else:
            return output_properties(**dataset_dict)
    elif output_metadata["history_content_type"] == "dataset_collection":
        if output_metadata["collection_type"] == "list":
            rval = []
            for element in output_metadata["elements"]:
                rval.append(element_to_cwl_json(element))
        elif output_metadata["collection_type"] == "record":
            rval = {}
            for element in output_metadata["elements"]:
                rval[element["element_identifier"]] = element_to_cwl_json(element)
        return rval
    else:
        raise NotImplementedError("Unknown history content type encountered")
