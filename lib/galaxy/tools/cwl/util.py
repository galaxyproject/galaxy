"""Client-centric CWL-related utilities.

Used to share code between the Galaxy test framework
and other Galaxy CWL clients (e.g. Planemo)."""
import hashlib
import json
import os
import tarfile
import tempfile
from collections import namedtuple

from six import BytesIO, iteritems, python_2_unicode_compatible

STORE_SECONDARY_FILES_WITH_BASENAME = True
SECONDARY_FILES_EXTRA_PREFIX = "__secondary_files__"
SECONDARY_FILES_INDEX_PATH = "__secondary_files_index.json"


def set_basename_and_derived_properties(properties, basename):
    properties["basename"] = basename
    properties["nameroot"], properties["nameext"] = os.path.splitext(basename)
    return properties


def output_properties(path=None, content=None, basename=None, pseduo_location=False):
    checksum = hashlib.sha1()
    properties = {
        "class": "File",
    }
    if path is not None:
        properties["path"] = path
        f = open(path, "rb")
    else:
        f = BytesIO(content)

    try:
        contents = f.read(1024 * 1024)
        filesize = 0
        while len(contents) > 0:
            checksum.update(contents)
            filesize += len(contents)
            contents = f.read(1024 * 1024)
    finally:
        f.close()
    properties["checksum"] = "sha1$%s" % checksum.hexdigest()
    properties["size"] = filesize
    set_basename_and_derived_properties(properties, basename)
    _handle_pseudo_location(properties, pseduo_location)
    return properties


def _handle_pseudo_location(properties, pseduo_location):
    if pseduo_location:
        properties["location"] = properties["basename"]


def galactic_job_json(
    job, test_data_directory, upload_func, collection_create_func, tool_or_workflow="workflow"
):
    """Adapt a CWL job object to the Galaxy API.

    CWL derived tools in Galaxy can consume a job description sort of like
    CWL job objects via the API but paths need to be replaced with datasets
    and records and arrays with collection references. This function will
    stage files and modify the job description to adapt to these changes
    for Galaxy.
    """

    datasets = []
    dataset_collections = []

    def upload_file(file_path, secondary_files):
        if not os.path.isabs(file_path):
            file_path = os.path.join(test_data_directory, file_path)
        _ensure_file_exists(file_path)
        target = FileUploadTarget(file_path, secondary_files)
        upload_response = upload_func(target)
        dataset = upload_response["outputs"][0]
        datasets.append((dataset, target))
        dataset_id = dataset["id"]
        return {"src": "hda", "id": dataset_id}

    def upload_tar(file_path):
        if not os.path.isabs(file_path):
            file_path = os.path.join(test_data_directory, file_path)
        _ensure_file_exists(file_path)
        target = DirectoryUploadTarget(file_path)
        upload_response = upload_func(target)
        dataset = upload_response["outputs"][0]
        datasets.append((dataset, target))
        dataset_id = dataset["id"]
        return {"src": "hda", "id": dataset_id}

    def upload_object(the_object):
        target = ObjectUploadTarget(the_object)
        upload_response = upload_func(target)
        dataset = upload_response["outputs"][0]
        datasets.append((dataset, target))
        dataset_id = dataset["id"]
        return {"src": "hda", "id": dataset_id}

    def replacement_item(value, force_to_file=False):
        is_dict = isinstance(value, dict)
        item_class = None if not is_dict else value.get("class", None)
        is_file = item_class == "File"
        is_directory = item_class == "Directory"

        if force_to_file:
            if is_file:
                return replacement_file(value)
            else:
                return upload_object(value)

        if isinstance(value, list):
            return replacement_list(value)
        elif not isinstance(value, dict):
            if tool_or_workflow == "workflow":
                # All inputs represented as dataset or collection parameters
                return upload_object(value)
            else:
                return value

        if is_file:
            return replacement_file(value)
        elif is_directory:
            return replacement_directory(value)
        else:
            return replacement_record(value)

    def replacement_file(value):
        file_path = value.get("location", None) or value.get("path", None)
        if file_path is None:
            return value

        secondary_files = value.get("secondaryFiles", [])
        secondary_files_tar_path = None
        if secondary_files:
            tmp = tempfile.NamedTemporaryFile(delete=False)
            tf = tarfile.open(fileobj=tmp, mode='w:')
            order = []
            index_contents = {
                "order": order
            }
            for secondary_file in secondary_files:
                secondary_file_path = secondary_file.get("location", None) or secondary_file.get("path", None)
                assert secondary_file_path, "Invalid secondaryFile entry found [%s]" % secondary_file
                full_secondary_file_path = os.path.join(test_data_directory, secondary_file_path)
                basename = secondary_file.get("basename") or os.path.basename(secondary_file_path)
                order.append(basename)
                tf.add(full_secondary_file_path, os.path.join(SECONDARY_FILES_EXTRA_PREFIX, basename))
            tmp_index = tempfile.NamedTemporaryFile(delete=False)
            json.dump(index_contents, tmp_index)
            tmp_index.close()
            tf.add(tmp_index.name, SECONDARY_FILES_INDEX_PATH)
            tf.close()
            secondary_files_tar_path = tmp.name

        return upload_file(file_path, secondary_files_tar_path)

    def replacement_directory(value):
        file_path = value.get("location", None) or value.get("path", None)
        if file_path is None:
            return value

        if not os.path.isabs(file_path):
            file_path = os.path.join(test_data_directory, file_path)

        tmp = tempfile.NamedTemporaryFile(delete=False)
        tf = tarfile.open(fileobj=tmp, mode='w:')
        tf.add(file_path, '.')
        tf.close()

        return upload_tar(tmp.name)

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


@python_2_unicode_compatible
class FileUploadTarget(object):

    def __init__(self, path, secondary_files=None):
        self.path = path
        self.secondary_files = secondary_files

    def __str__(self):
        return "FileUploadTarget[path=%s]" % self.path


@python_2_unicode_compatible
class ObjectUploadTarget(object):

    def __init__(self, the_object):
        self.object = the_object

    def __str__(self):
        return "ObjectUploadTarget[object=%s]" % self.object


@python_2_unicode_compatible
class DirectoryUploadTarget(object):

    def __init__(self, tar_path):
        self.tar_path = tar_path

    def __str__(self):
        return "DirectoryUploadTarget[tar_path=%s]" % self.tar_path


GalaxyOutput = namedtuple("GalaxyOutput", ["history_id", "history_content_type", "history_content_id"])


def tool_response_to_output(tool_response, history_id, output_id):
    for output in tool_response["outputs"]:
        if output["output_name"] == output_id:
            return GalaxyOutput(history_id, "dataset", output["id"])

    for output_collection in tool_response["output_collections"]:
        if output_collection["output_name"] == output_id:
            return GalaxyOutput(history_id, "dataset_collection", output_collection["id"])

    raise Exception("Failed to find output with label [%s]" % output_id)


def invocation_to_output(invocation, history_id, output_id):
    if output_id in invocation["outputs"]:
        dataset = invocation["outputs"][output_id]
        galaxy_output = GalaxyOutput(history_id, "dataset", dataset["id"])
    elif output_id in invocation["output_collections"]:
        collection = invocation["output_collections"][output_id]
        galaxy_output = GalaxyOutput(history_id, "dataset_collection", collection["id"])
    else:
        raise Exception("Failed to find output with label [%s] in [%s]" % (output_id, invocation))

    return galaxy_output


def output_to_cwl_json(
    galaxy_output, get_metadata, get_dataset, get_extra_files, pseduo_location=False,
):
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
        return output_to_cwl_json(element_output, get_metadata, get_dataset, get_extra_files)

    output_metadata = get_metadata(galaxy_output.history_content_type, galaxy_output.history_content_id)

    def dataset_dict_to_json_content(dataset_dict):
        if "content" in dataset_dict:
            return json.loads(dataset_dict["content"])
        else:
            with open(dataset_dict["path"]) as f:
                return json.load(f)

    if output_metadata["history_content_type"] == "dataset":
        ext = output_metadata["file_ext"]
        assert output_metadata["state"] == "ok"
        if ext == "expression.json":
            dataset_dict = get_dataset(output_metadata)
            return dataset_dict_to_json_content(dataset_dict)
        else:
            file_or_directory = "Directory" if ext == "directory" else "File"
            if file_or_directory == "File":
                dataset_dict = get_dataset(output_metadata)
                properties = output_properties(pseduo_location=pseduo_location, **dataset_dict)
                basename = properties["basename"]
                extra_files = get_extra_files(output_metadata)
                found_index = False
                for extra_file in extra_files:
                    if extra_file["class"] == "File":
                        path = extra_file["path"]
                        if path == SECONDARY_FILES_INDEX_PATH:
                            found_index = True

                if found_index:
                    ec = get_dataset(output_metadata, filename=SECONDARY_FILES_INDEX_PATH)
                    index = dataset_dict_to_json_content(ec)
                    for basename in index["order"]:
                        for extra_file in extra_files:
                            if extra_file["class"] == "File":
                                path = extra_file["path"]
                                if path == os.path.join(SECONDARY_FILES_EXTRA_PREFIX, basename):
                                    ec = get_dataset(output_metadata, filename=path)
                                    if not STORE_SECONDARY_FILES_WITH_BASENAME:
                                        ec["basename"] = basename + os.path.basename(path)
                                    else:
                                        ec["basename"] = os.path.basename(path)
                                    ec_properties = output_properties(pseduo_location=pseduo_location, **ec)
                                    if "secondaryFiles" not in properties:
                                        properties["secondaryFiles"] = []

                                    properties["secondaryFiles"].append(ec_properties)
            else:
                basename = output_metadata.get("cwl_file_name")
                if not basename:
                    basename = output_metadata.get("name")

                listing = []
                properties = {
                    "class": "Directory",
                    "basename": basename,
                    "listing": listing,
                }

                extra_files = get_extra_files(output_metadata)
                for extra_file in extra_files:
                    if extra_file["class"] == "File":
                        path = extra_file["path"]
                        ec = get_dataset(output_metadata, filename=path)
                        ec["basename"] = os.path.basename(path)
                        ec_properties = output_properties(pseduo_location=pseduo_location, **ec)
                        listing.append(ec_properties)

            return properties

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
