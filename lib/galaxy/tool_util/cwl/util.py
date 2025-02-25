"""Client-centric CWL-related utilities.

Used to share code between the Galaxy test framework
and other Galaxy CWL clients (e.g. Planemo)."""

import abc
import hashlib
import io
import json
import os
import tarfile
import tempfile
import urllib.parse
from collections import namedtuple
from typing import (
    Any,
    BinaryIO,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
)

import yaml
from typing_extensions import (
    Literal,
    TypedDict,
)

from galaxy.util import (
    str_removeprefix,
    unicodify,
)

STORE_SECONDARY_FILES_WITH_BASENAME = True
SECONDARY_FILES_EXTRA_PREFIX = "__secondary_files__"
SECONDARY_FILES_INDEX_PATH = "__secondary_files_index.json"


def set_basename_and_derived_properties(properties, basename):
    properties["basename"] = basename
    properties["nameroot"], properties["nameext"] = os.path.splitext(basename)
    return properties


OutputPropertiesType = TypedDict(
    "OutputPropertiesType",
    {
        "class": str,
        "location": Optional[str],
        "path": Optional[str],
        "listing": Optional[List[Any]],
        "basename": Optional[str],
        "nameroot": Optional[str],
        "nameext": Optional[str],
        "secondaryFiles": List[Any],
        "checksum": str,
        "size": int,
    },
    total=False,
)


def output_properties(
    path: Optional[str] = None,
    content: Optional[bytes] = None,
    basename=None,
    pseudo_location=False,
) -> OutputPropertiesType:
    checksum = hashlib.sha1()
    properties: OutputPropertiesType = {"class": "File", "checksum": "", "size": 0}
    f: BinaryIO
    if path is not None:
        properties["path"] = path
        f = open(path, "rb")
    else:
        if content is None:
            raise Exception("If no 'path', must provide 'content'.")
        f = io.BytesIO(content)

    try:
        contents = f.read(1024 * 1024)
        filesize = 0
        while contents:
            checksum.update(contents)
            filesize += len(contents)
            contents = f.read(1024 * 1024)
    finally:
        f.close()
    properties["checksum"] = f"sha1${checksum.hexdigest()}"
    properties["size"] = filesize
    set_basename_and_derived_properties(properties, basename)
    _handle_pseudo_location(properties, pseudo_location)
    return properties


def _handle_pseudo_location(properties, pseudo_location):
    if pseudo_location:
        properties["location"] = properties["basename"]


def abs_path_or_uri(path_or_uri: str, relative_to: str, resolve_data: Optional[Callable[[str], Optional[str]]]) -> str:
    """Return the absolute path if this isn't a URI, otherwise keep the URI the same."""
    if "://" in path_or_uri:
        return path_or_uri
    abs_path_ = os.path.abspath(os.path.join(relative_to, path_or_uri))
    if resolve_data and not os.path.exists(abs_path_):
        if resolved_data := resolve_data(path_or_uri):
            abs_path_ = resolved_data
    _ensure_file_exists(abs_path_)
    return abs_path_


def abs_path(path_or_uri: str, relative_to: str) -> str:
    """Return the absolute path if this is a file:// URI or a local path."""
    if path_or_uri.startswith("file://"):
        # The path after file:// must be absolute
        abs_path_ = path_or_uri[len("file://") :]
    else:
        index = path_or_uri.find("://")
        if index != -1:
            raise ValueError(f"Unsupported URI scheme: {path_or_uri[: index + 3]}")
        abs_path_ = os.path.abspath(os.path.join(relative_to, path_or_uri))
    _ensure_file_exists(abs_path_)
    return abs_path_


def path_or_uri_to_uri(path_or_uri: str) -> str:
    if "://" not in path_or_uri:
        return f"file://{path_or_uri}"
    else:
        return path_or_uri


def galactic_job_json(
    job: Dict[str, Any],
    test_data_directory: str,
    upload_func: Callable[["UploadTarget"], Dict[str, Any]],
    collection_create_func: Callable[[List[Dict[str, Any]], str], Dict[str, Any]],
    tool_or_workflow: Literal["tool", "workflow"] = "workflow",
    resolve_data: Optional[Callable[[str], Optional[str]]] = None,
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """Adapt a CWL job object to the Galaxy API.

    CWL derived tools in Galaxy can consume a job description sort of like
    CWL job objects via the API but paths need to be replaced with datasets
    and records and arrays with collection references. This function will
    stage files and modify the job description to adapt to these changes
    for Galaxy.
    """

    datasets: List[Dict[str, Any]] = []
    dataset_collections: List[Dict[str, Any]] = []

    def response_to_hda(target: UploadTarget, upload_response: Dict[str, Any]) -> Dict[str, str]:
        assert isinstance(upload_response, dict), upload_response
        assert "outputs" in upload_response, upload_response
        assert len(upload_response["outputs"]) > 0, upload_response
        dataset = upload_response["outputs"][0]
        datasets.append(dataset)
        dataset_id = dataset["id"]
        return {"src": "hda", "id": dataset_id}

    def upload_file(file_path: str, secondary_files: Optional[str], **kwargs) -> Dict[str, str]:
        file_path = abs_path_or_uri(file_path, test_data_directory, resolve_data=resolve_data)
        target = FileUploadTarget(file_path, secondary_files, **kwargs)
        upload_response = upload_func(target)
        return response_to_hda(target, upload_response)

    def upload_file_literal(contents: str, **kwd) -> Dict[str, str]:
        target = FileLiteralTarget(contents, **kwd)
        upload_response = upload_func(target)
        return response_to_hda(target, upload_response)

    def upload_tar(file_path: str, file_type: str = "directory", name: str = "uploaded tar file") -> Dict[str, str]:
        file_path = abs_path_or_uri(file_path, test_data_directory, resolve_data=resolve_data)
        target = DirectoryUploadTarget(file_path, file_type=file_type, name=name)
        upload_response = upload_func(target)
        return response_to_hda(target, upload_response)

    def upload_file_with_composite_data(file_path: Optional[str], composite_data, **kwargs) -> Dict[str, str]:
        if file_path is not None:
            file_path = abs_path_or_uri(file_path, test_data_directory, resolve_data=resolve_data)
        composite_data_resolved = []
        for cd in composite_data:
            composite_data_resolved.append(abs_path_or_uri(cd, test_data_directory, resolve_data=resolve_data))
        target = FileUploadTarget(file_path, composite_data=composite_data_resolved, **kwargs)
        upload_response = upload_func(target)
        return response_to_hda(target, upload_response)

    def upload_object(the_object: Any) -> Dict[str, str]:
        target = ObjectUploadTarget(the_object)
        upload_response = upload_func(target)
        return response_to_hda(target, upload_response)

    def replacement_item(value, force_to_file: bool = False):
        is_dict = isinstance(value, dict)
        item_class = None if not is_dict else value.get("class", None)
        is_file = item_class == "File"
        is_directory = item_class == "Directory"
        is_collection = item_class == "Collection"  # Galaxy extension.

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
        elif is_collection:
            return replacement_collection(value)
        else:
            return replacement_record(value)

    def replacement_file(value):
        if value.get("galaxy_id"):
            return {"src": "hda", "id": str(value["galaxy_id"])}
        file_path = value.get("location") or value.get("path")
        # format to match output definitions in tool, where did filetype come from?
        filetype = value.get("filetype", None) or value.get("format", None)
        composite_data_raw = value.get("composite_data", None)
        kwd = {}
        if "tags" in value:
            kwd["tags"] = value.get("tags")
        if "dbkey" in value:
            kwd["dbkey"] = value.get("dbkey")
        if "decompress" in value:
            kwd["decompress"] = value["decompress"]
        if value.get("hashes"):
            kwd["hashes"] = value["hashes"]
        if composite_data_raw:
            composite_data = []
            for entry in composite_data_raw:
                path = None
                if isinstance(entry, dict):
                    path = entry.get("location", None) or entry.get("path", None)
                else:
                    path = entry
                composite_data.append(path)
            rval_c = upload_file_with_composite_data(None, composite_data, filetype=filetype, **kwd)
            return rval_c

        if file_path is None:
            contents = value.get("contents")
            if contents is not None:
                return upload_file_literal(contents, **kwd)

            return value

        secondary_files = value.get("secondaryFiles", [])
        secondary_files_tar_path = None
        if secondary_files:
            tmp = tempfile.NamedTemporaryFile(delete=False)
            tf = tarfile.open(fileobj=tmp, mode="w:")
            order: List[str] = []
            index_contents = {"order": order}
            for secondary_file in secondary_files:
                secondary_file_path = secondary_file.get("location", None) or secondary_file.get("path", None)
                assert secondary_file_path, f"Invalid secondaryFile entry found [{secondary_file}]"
                full_secondary_file_path = os.path.join(test_data_directory, secondary_file_path)
                basename = secondary_file.get("basename") or os.path.basename(secondary_file_path)
                order.append(unicodify(basename))
                tf.add(full_secondary_file_path, os.path.join(SECONDARY_FILES_EXTRA_PREFIX, basename))
            tmp_index = tempfile.NamedTemporaryFile(delete=False, mode="w")
            json.dump(index_contents, tmp_index)
            tmp_index.close()
            tf.add(tmp_index.name, SECONDARY_FILES_INDEX_PATH)
            tf.close()
            secondary_files_tar_path = tmp.name

        return upload_file(file_path, secondary_files_tar_path, filetype=filetype, **kwd)

    def replacement_directory(value: Dict[str, Any]) -> Dict[str, Any]:
        file_path = value.get("location", None) or value.get("path", None)
        if file_path is None:
            return value
        if not os.path.isabs(file_path):
            file_path = os.path.join(test_data_directory, file_path)

        file_type = value.get("filetype", None) or value.get("format", None) or "directory"

        tmp = tempfile.NamedTemporaryFile(delete=False)
        tf = tarfile.open(fileobj=tmp, mode="w:")
        tf.add(file_path, ".")
        tf.close()

        return upload_tar(tmp.name, file_type=file_type, name=os.path.basename(file_path))

    def replacement_list(value) -> Dict[str, str]:
        collection_element_identifiers = []
        for i, item in enumerate(value):
            dataset = replacement_item(item, force_to_file=True)
            collection_element = dataset.copy()
            collection_element["name"] = str(i)
            collection_element_identifiers.append(collection_element)

        # TODO: handle nested lists/arrays
        collection = collection_create_func(collection_element_identifiers, "list")
        dataset_collections.append(collection)
        hdca_id = collection["id"]
        return {"src": "hdca", "id": hdca_id}

    def to_elements(value, rank_collection_type: str) -> List[Dict[str, Any]]:
        collection_element_identifiers = []
        assert "elements" in value
        elements = value["elements"]

        is_nested_collection = ":" in rank_collection_type
        for element in elements:
            if not is_nested_collection:
                # flat collection
                dataset = replacement_item(element, force_to_file=True)
                collection_element = dataset.copy()
                collection_element["name"] = element["identifier"]
                collection_element_identifiers.append(collection_element)
            else:
                # nested collection
                sub_collection_type = rank_collection_type[rank_collection_type.find(":") + 1 :]
                collection_element = {
                    "name": element["identifier"],
                    "src": "new_collection",
                    "collection_type": sub_collection_type,
                    "element_identifiers": to_elements(element, sub_collection_type),
                }
                collection_element_identifiers.append(collection_element)

        return collection_element_identifiers

    def replacement_collection(value: Dict[str, Any]) -> Dict[str, str]:
        if value.get("galaxy_id"):
            return {"src": "hdca", "id": str(value["galaxy_id"])}
        assert "collection_type" in value
        collection_type = value["collection_type"]
        elements = to_elements(value, collection_type)

        collection = collection_create_func(elements, collection_type)
        dataset_collections.append(collection)
        hdca_id = collection["id"]
        return {"src": "hdca", "id": hdca_id}

    def replacement_record(value):
        collection_element_identifiers = []
        for record_key, record_value in value.items():
            if not isinstance(record_value, dict) or record_value.get("class") != "File":
                dataset = replacement_item(record_value, force_to_file=True)
                collection_element = dataset.copy()
            else:
                dataset = upload_file(record_value["location"], None)
                collection_element = dataset.copy()

            collection_element["name"] = record_key
            collection_element_identifiers.append(collection_element)

        collection = collection_create_func(collection_element_identifiers, "record")
        dataset_collections.append(collection)
        hdca_id = collection["id"]
        return {"src": "hdca", "id": hdca_id}

    replace_keys = {}
    for key, value in job.items():
        replace_keys[key] = replacement_item(value)

    job.update(replace_keys)
    return job, datasets


def _ensure_file_exists(file_path: str) -> None:
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


class UploadTarget:
    @abc.abstractmethod
    def __str__(self) -> str:
        pass


class FileLiteralTarget(UploadTarget):
    def __init__(self, contents: str, **kwargs) -> None:
        self.contents = contents
        self.properties = kwargs

    def __str__(self) -> str:
        return f"FileLiteralTarget[contents={self.contents}] with {self.properties}"


class FileUploadTarget(UploadTarget):
    def __init__(
        self,
        path: Optional[str],
        secondary_files: Optional[str] = None,
        composite_data: Optional[List[str]] = None,
        **kwargs,
    ) -> None:
        self.path = path
        self.secondary_files = secondary_files
        self.composite_data = composite_data
        self.properties = kwargs

    def __str__(self) -> str:
        return f"FileUploadTarget[path={self.path}] with {self.properties}"


class ObjectUploadTarget(UploadTarget):
    def __init__(self, the_object: Any) -> None:
        self.object = the_object
        self.properties: Dict = {}

    def __str__(self) -> str:
        return f"ObjectUploadTarget[object={self.object}] with {self.properties}"


class DirectoryUploadTarget(UploadTarget):
    def __init__(self, tar_path: str, file_type: str = "directory", name: str = "uploaded directory") -> None:
        self.tar_path = tar_path
        self.file_type = file_type
        self.name = name

    def __str__(self) -> str:
        return f"DirectoryUploadTarget[tar_path={self.tar_path}]"


GalaxyOutput = namedtuple("GalaxyOutput", ["history_id", "history_content_type", "history_content_id", "metadata"])


def tool_response_to_output(tool_response, history_id, output_name):
    for output in tool_response["outputs"]:
        if output["output_name"] == output_name:
            return GalaxyOutput(history_id, "dataset", output["id"], None)

    for output_collection in tool_response["output_collections"]:
        if output_collection["output_name"] == output_name:
            return GalaxyOutput(history_id, "dataset_collection", output_collection["id"], None)

    raise Exception(f"Failed to find output with label [{output_name}]")


def invocation_to_output(invocation, history_id, output_name):
    if output_name in invocation["outputs"]:
        dataset = invocation["outputs"][output_name]
        return GalaxyOutput(history_id, "dataset", dataset["id"], None)
    elif output_name in invocation["output_collections"]:
        collection = invocation["output_collections"][output_name]
        return GalaxyOutput(history_id, "dataset_collection", collection["id"], None)
    elif output_name in invocation["output_values"]:
        output_value = invocation["output_values"][output_name]
        return GalaxyOutput(None, "raw_value", output_value, None)
    raise Exception(f"Failed to find output with label [{output_name}] in [{invocation}]")


def output_to_cwl_json(
    galaxy_output,
    get_metadata,
    get_dataset,
    get_extra_files,
    pseudo_location=False,
):
    """Convert objects in a Galaxy history into a CWL object.

    Useful in running conformance tests and implementing the cwl-runner
    interface via Galaxy.
    """

    def element_to_cwl_json(element):
        object = element["object"]
        content_type = object.get("history_content_type")
        metadata = None
        if content_type is None:
            content_type = "dataset_collection"
            metadata = element["object"]
            metadata["history_content_type"] = content_type
        element_output = GalaxyOutput(
            galaxy_output.history_id,
            content_type,
            object["id"],
            metadata,
        )
        return output_to_cwl_json(
            element_output, get_metadata, get_dataset, get_extra_files, pseudo_location=pseudo_location
        )

    output_metadata = galaxy_output.metadata
    if output_metadata is None:
        output_metadata = get_metadata(galaxy_output.history_content_type, galaxy_output.history_content_id)

    def dataset_dict_to_json_content(dataset_dict):
        if "content" in dataset_dict:
            return json.loads(dataset_dict["content"])
        else:
            with open(dataset_dict["path"]) as f:
                return json.load(f)

    if galaxy_output.history_content_type == "raw_value":
        return galaxy_output.history_content_id
    elif output_metadata["history_content_type"] == "dataset":
        ext = output_metadata["file_ext"]
        if ext == "expression.json":
            dataset_dict = get_dataset(output_metadata)
            return dataset_dict_to_json_content(dataset_dict)
        else:
            file_or_directory = "Directory" if ext == "directory" else "File"
            secondary_files = []

            if file_or_directory == "File":
                dataset_dict = get_dataset(output_metadata)
                properties = output_properties(pseudo_location=pseudo_location, **dataset_dict)
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

                    def dir_listing(dir_path):
                        listing = []
                        for extra_file in extra_files:
                            path = extra_file["path"]
                            extra_file_class = extra_file["class"]
                            extra_file_basename = os.path.basename(path)
                            if os.path.join(dir_path, extra_file_basename) != path:
                                continue

                            if extra_file_class == "File":
                                ec = get_dataset(output_metadata, filename=path)
                                ec["basename"] = extra_file_basename
                                ec_properties = output_properties(pseudo_location=pseudo_location, **ec)
                            elif extra_file_class == "Directory":
                                ec_properties = {}
                                ec_properties["class"] = "Directory"
                                ec_properties["location"] = ec_basename
                                ec_properties["listing"] = dir_listing(path)
                            else:
                                raise Exception("Unknown output type encountered....")
                            listing.append(ec_properties)
                        return listing

                    for basename in index["order"]:
                        for extra_file in extra_files:
                            path = extra_file["path"]
                            if path != os.path.join(SECONDARY_FILES_EXTRA_PREFIX, basename or ""):
                                continue

                            extra_file_class = extra_file["class"]

                            # This is wrong...
                            if not STORE_SECONDARY_FILES_WITH_BASENAME:
                                ec_basename = basename + os.path.basename(path)
                            else:
                                ec_basename = os.path.basename(path)

                            if extra_file_class == "File":
                                ec = get_dataset(output_metadata, filename=path)
                                ec["basename"] = ec_basename
                                ec_properties = output_properties(pseudo_location=pseudo_location, **ec)
                            elif extra_file_class == "Directory":
                                ec_properties = {}
                                ec_properties["class"] = "Directory"
                                ec_properties["location"] = ec_basename
                                ec_properties["listing"] = dir_listing(path)
                            else:
                                raise Exception("Unknown output type encountered....")
                            secondary_files.append(ec_properties)

            else:
                basename = output_metadata.get("created_from_basename")
                if not basename:
                    basename = output_metadata.get("name")

                listing: List[OutputPropertiesType] = []
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
                        ec_properties = output_properties(pseudo_location=pseudo_location, **ec)
                        listing.append(ec_properties)

            if secondary_files:
                properties["secondaryFiles"] = secondary_files
            return properties

    elif output_metadata["history_content_type"] == "dataset_collection":
        collection_type = output_metadata["collection_type"].split(":", 1)[0]
        if collection_type in ["list", "paired"]:
            rval_l = []
            for element in output_metadata["elements"]:
                rval_l.append(element_to_cwl_json(element))
            return rval_l
        elif collection_type == "record":
            rval_d = {}
            for element in output_metadata["elements"]:
                rval_d[element["element_identifier"]] = element_to_cwl_json(element)
            return rval_d
        return None
    else:
        raise NotImplementedError("Unknown history content type encountered")


def download_output(galaxy_output, get_metadata, get_dataset, get_extra_files, output_path):
    output_metadata = get_metadata(galaxy_output.history_content_type, galaxy_output.history_content_id)
    dataset_dict = get_dataset(output_metadata)
    with open(output_path, "wb") as fh:
        fh.write(dataset_dict["content"])


def guess_artifact_type(path):
    tool_or_workflow = "workflow"
    path, object_id = urllib.parse.urldefrag(path)
    with open(path) as f:
        document = yaml.safe_load(f)

    if "$graph" in document:
        # Packed document without a process object at the root
        objects = document["$graph"]
        if not object_id:
            object_id = "main"  # default object id

        # Have to use str_removeprefix() instead of rstrip() because only the
        # first '#' should be removed from the object id
        matching_objects = [o for o in objects if str_removeprefix(o["id"], "#") == object_id]
        if len(matching_objects) == 0:
            raise Exception(f"No process object with id [{object_id}]")
        if len(matching_objects) > 1:
            raise Exception(f"Multiple process objects with id [{object_id}]")
        object_ = matching_objects[0]
    else:
        object_ = document

    tool_or_workflow = "tool" if object_["class"] != "Workflow" else "workflow"

    return tool_or_workflow
