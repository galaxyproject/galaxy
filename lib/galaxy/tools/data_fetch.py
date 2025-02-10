import argparse
import errno
import json
import os
import shutil
import sys
import tempfile
from io import StringIO
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

import bdbag.bdbag_api

from galaxy.datatypes import sniff
from galaxy.datatypes.registry import Registry
from galaxy.datatypes.upload_util import (
    handle_upload,
    UploadProblemException,
)
from galaxy.files.uris import (
    ensure_file_sources,
    stream_to_file,
    stream_url_to_file,
)
from galaxy.util import (
    in_directory,
    safe_makedirs,
)
from galaxy.util.bunch import Bunch
from galaxy.util.compression_utils import CompressedFile
from galaxy.util.hash_util import (
    HASH_NAMES,
    HashFunctionNameEnum,
    verify_hash,
)

DESCRIPTION = """Data Import Script"""


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    args = _arg_parser().parse_args(argv)
    registry = Registry()
    registry.load_datatypes(root_dir=args.galaxy_root, config=args.datatypes_registry)
    do_fetch(args.request, working_directory=args.working_directory or os.getcwd(), registry=registry)


def do_fetch(
    request_path: str,
    working_directory: str,
    registry: Registry,
    file_sources_dict: Optional[Dict] = None,
):
    assert os.path.exists(request_path)
    with open(request_path) as f:
        request = json.load(f)

    allow_failed_collections = request.get("allow_failed_collections", False)
    upload_config = UploadConfig(
        request,
        registry,
        working_directory,
        allow_failed_collections,
        file_sources_dict,
    )
    galaxy_json = _request_to_galaxy_json(upload_config, request)
    galaxy_json_path = os.path.join(working_directory, "galaxy.json")
    with open(galaxy_json_path, "w") as f:
        json.dump(galaxy_json, f)
    return working_directory


def _request_to_galaxy_json(upload_config: "UploadConfig", request):
    targets = request.get("targets", [])
    fetched_targets = []

    for target in targets:
        fetched_target = _fetch_target(upload_config, target)
        fetched_targets.append(fetched_target)

    return {"__unnamed_outputs": fetched_targets}


def _fetch_target(upload_config: "UploadConfig", target: Dict[str, Any]):
    destination = target.get("destination", None)
    assert destination, "No destination defined."

    def expand_elements_from(target_or_item):
        items = None
        if elements_from := target_or_item.get("elements_from", None):
            if elements_from == "archive":
                decompressed_directory = _decompress_target(upload_config, target_or_item)
                items = _directory_to_items(decompressed_directory)
            elif elements_from == "bagit":
                _, elements_from_path, _ = _has_src_to_path(upload_config, target_or_item, is_dataset=False)
                items = _bagit_to_items(elements_from_path)
            elif elements_from == "bagit_archive":
                decompressed_directory = _decompress_target(upload_config, target_or_item)
                items = _bagit_to_items(decompressed_directory)
            elif elements_from == "directory":
                _, elements_from_path, _ = _has_src_to_path(upload_config, target_or_item, is_dataset=False)
                items = _directory_to_items(elements_from_path)
            else:
                raise Exception(f"Unknown elements from type encountered [{elements_from}]")

        if items:
            del target_or_item["elements_from"]
            target_or_item["elements"] = items

    expansion_error = None
    try:
        _for_each_src(expand_elements_from, target)
    except Exception as e:
        expansion_error = f"Error expanding elements/items for upload destination. {str(e)}"

    if expansion_error is None:
        items = target.get("elements", None)
        assert items is not None, f"No element definition found for destination [{destination}]"
    else:
        items = []

    fetched_target = {}
    fetched_target["destination"] = destination
    destination_type = destination["type"]
    is_collection = destination_type == "hdca"
    failed_elements = []

    if "collection_type" in target:
        fetched_target["collection_type"] = target["collection_type"]
    if "name" in target:
        fetched_target["name"] = target["name"]

    def _copy_and_validate_simple_attributes(src_item, target_metadata):
        info = src_item.get("info", None)
        created_from_basename = src_item.get("created_from_basename", None)
        tags = src_item.get("tags", [])

        if info is not None:
            target_metadata["info"] = info
        if (object_id := src_item.get("object_id", None)) is not None:
            target_metadata["object_id"] = object_id
        if tags:
            target_metadata["tags"] = tags
        if created_from_basename:
            target_metadata["created_from_basename"] = created_from_basename
        if "error_message" in src_item:
            target_metadata["error_message"] = src_item["error_message"]
        return target_metadata

    def _resolve_item(item):
        # Might be a dataset or a composite upload.
        requested_ext = item.get("ext", None)
        registry = upload_config.registry
        datatype = registry.get_datatype_by_extension(requested_ext)
        composite = item.pop("composite", None)
        if datatype and datatype.composite_type:
            composite_type = datatype.composite_type
            assert composite_type == "auto_primary_file", "basic composite uploads not yet implemented"

            # get_composite_dataset_name finds dataset name from basename of contents
            # and such but we're not implementing that here yet. yagni?
            # also need name...
            metadata = {
                composite_file.substitute_name_with_metadata: datatype.metadata_spec[
                    composite_file.substitute_name_with_metadata
                ].default
                for composite_file in datatype.composite_files.values()
                if composite_file.substitute_name_with_metadata
            }
            name = item.get("name") or "Composite Dataset"
            metadata["base_name"] = name
            dataset = Bunch(
                name=name,
                metadata=metadata,
            )
            writable_files = datatype.get_writable_files_for_dataset(dataset)
            primary_file = stream_to_file(
                StringIO(datatype.generate_primary_file(dataset)),
                prefix="upload_auto_primary_file",
                dir=upload_config.working_directory,
            )
            extra_files_path = f"{primary_file}_extra"
            os.mkdir(extra_files_path)
            rval: Dict[str, Any] = {
                "name": name,
                "filename": primary_file,
                "ext": requested_ext,
                "link_data_only": False,
                "sources": [],
                "hashes": [],
                "extra_files": extra_files_path,
            }
            _copy_and_validate_simple_attributes(item, rval)
            composite_items = composite.get("elements", [])
            keys = list(writable_files.keys())
            composite_item_idx = 0
            for composite_item in composite_items:
                if composite_item_idx >= len(keys):
                    # raise exception - too many files?
                    pass
                key = keys[composite_item_idx]
                writable_file = writable_files[key]
                _, src_target, _ = _has_src_to_path(upload_config, composite_item)
                # do the writing
                sniff.handle_composite_file(
                    datatype,
                    src_target,
                    extra_files_path,
                    key,
                    writable_file.is_binary,
                    upload_config.working_directory,
                    f"{os.path.basename(extra_files_path)}_",
                    composite_item,
                )
                composite_item_idx += 1

            writable_files_idx = composite_item_idx
            while writable_files_idx < len(keys):
                key = keys[writable_files_idx]
                writable_file = writable_files[key]
                if not writable_file.optional:
                    # raise Exception, non-optional file missing
                    pass
                writable_files_idx += 1
            return rval
        else:
            if composite:
                raise Exception(f"Non-composite datatype [{datatype}] attempting to be created with composite data.")
            return _resolve_item_with_primary(item)

    def _resolve_item_with_primary(item):
        error_message = None
        converted_path = None

        deferred = upload_config.get_option(item, "deferred")

        link_data_only = upload_config.link_data_only
        link_data_only_explicit = upload_config.link_data_only_explicit
        if "link_data_only" in item:
            # Allow overriding this on a per file basis.
            link_data_only, link_data_only_explicit = _link_data_only(item)

        name: str
        path: Optional[str]
        default_in_place = False
        if not deferred:
            name, path, is_link = _has_src_to_path(
                upload_config, item, is_dataset=True, link_data_only_explicitly_set=link_data_only_explicit
            )
            if is_link:
                link_data_only = True
                default_in_place = True
        else:
            name, path = _has_src_to_name(item) or "Deferred Dataset", None
        sources = []

        url = item.get("url")
        source_dict = {"source_uri": url}
        if url:
            sources.append(source_dict)
        hashes = item.get("hashes", [])
        for hash_function in HASH_NAMES:
            hash_value = item.get(hash_function)
            if hash_value:
                hashes.append({"hash_function": hash_function, "hash_value": hash_value})
        if path:
            for hash_dict in hashes:
                hash_function = hash_dict.get("hash_function")
                hash_value = hash_dict.get("hash_value")
                try:
                    _handle_hash_validation(hash_function, hash_value, path)
                except Exception as e:
                    error_message = str(e)
                    item["error_message"] = error_message

        dbkey = item.get("dbkey", "?")

        ext = "data"
        staged_extra_files = None

        requested_ext = item.get("ext", "auto")
        to_posix_lines = upload_config.get_option(item, "to_posix_lines")
        space_to_tab = upload_config.get_option(item, "space_to_tab")
        auto_decompress = upload_config.get_option(item, "auto_decompress")

        effective_state = "ok"
        if not deferred and not error_message:
            in_place = item.get("in_place", default_in_place)
            purge_source = item.get("purge_source", True)

            registry = upload_config.registry
            check_content = upload_config.check_content
            assert path  # if deferred won't be in this branch.
            stdout, ext, datatype, is_binary, converted_path, converted_newlines, converted_spaces = handle_upload(
                registry=registry,
                path=path,
                requested_ext=requested_ext,
                name=name,
                tmp_prefix="data_fetch_upload_",
                tmp_dir=upload_config.working_directory,
                check_content=check_content,
                link_data_only=link_data_only,
                in_place=in_place,
                auto_decompress=auto_decompress,
                convert_to_posix_lines=to_posix_lines,
                convert_spaces_to_tabs=space_to_tab,
            )
            transform = []
            if converted_newlines:
                transform.append({"action": "to_posix_lines"})
            if converted_spaces:
                transform.append({"action": "spaces_to_tabs"})
            if link_data_only:
                # Never alter a file that will not be copied to Galaxy's local file store.
                if datatype.dataset_content_needs_grooming(path):
                    err_msg = (
                        "The uploaded files need grooming, so change your <b>Copy data into Galaxy?</b> selection to be "
                        "<b>Copy files into Galaxy</b> instead of <b>Link to files without copying into Galaxy</b> so grooming can be performed."
                    )
                    raise UploadProblemException(err_msg)

            # If this file is not in the workdir make sure it gets there.
            if not link_data_only and converted_path:
                path = upload_config.ensure_in_working_directory(converted_path, purge_source, in_place)
            elif not link_data_only:
                path = upload_config.ensure_in_working_directory(path, purge_source, in_place)

            extra_files = item.get("extra_files")
            if extra_files:
                # TODO: optimize to just copy the whole directory to extra files instead.
                assert not upload_config.link_data_only, "linking composite dataset files not yet implemented"
                extra_files_path = f"{path}_extra"
                staged_extra_files = extra_files_path
                os.mkdir(extra_files_path)

                def walk_extra_files(items, prefix=""):
                    for item in items:
                        if "elements" in item:
                            name = item.get("name")
                            if not prefix:
                                item_prefix = name
                            else:
                                item_prefix = os.path.join(prefix, name)
                            walk_extra_files(item.get("elements"), prefix=item_prefix)
                        else:
                            src_name, src_path, _ = _has_src_to_path(upload_config, item)
                            if prefix:
                                rel_path = os.path.join(prefix, src_name)
                            else:
                                rel_path = src_name

                            file_output_path = os.path.join(extra_files_path, rel_path)
                            parent_dir = os.path.dirname(file_output_path)
                            if not os.path.exists(parent_dir):
                                safe_makedirs(parent_dir)
                            shutil.move(src_path, file_output_path)

                walk_extra_files(extra_files.get("elements", []))

            # TODO:
            # in galaxy json add 'extra_files' and point at target derived from extra_files:

            needs_grooming = not link_data_only and datatype and datatype.dataset_content_needs_grooming(path)
            if needs_grooming:
                # Groom the dataset content if necessary
                transform.append(
                    {"action": "datatype_groom", "datatype_ext": ext, "datatype_class": datatype.__class__.__name__}
                )
                assert path
                datatype.groom_dataset_content(path)

            if len(transform) > 0:
                source_dict["transform"] = transform
        elif not error_message:
            transform = []
            if to_posix_lines:
                transform.append({"action": "to_posix_lines"})
            if space_to_tab:
                transform.append({"action": "spaces_to_tabs"})
            effective_state = "deferred"
            registry = upload_config.registry
            ext = sniff.guess_ext_from_file_name(name, registry=registry, requested_ext=requested_ext)
        rval = {
            "name": name,
            "dbkey": dbkey,
            "ext": ext,
            "link_data_only": link_data_only,
            "sources": sources,
            "hashes": hashes,
            "info": f"uploaded {ext} file",
            "state": effective_state,
        }
        if path:
            rval["filename"] = path
        if staged_extra_files:
            rval["extra_files"] = os.path.abspath(staged_extra_files)
        return _copy_and_validate_simple_attributes(item, rval)

    def _resolve_item_capture_error(item):
        try:
            return _resolve_item(item)
        except Exception as e:
            rval = {"error_message": str(e)}
            rval = _copy_and_validate_simple_attributes(item, rval)
            failed_elements.append(rval)
            return rval

    if expansion_error is None:
        elements = elements_tree_map(_resolve_item_capture_error, items)
        if is_collection and not upload_config.allow_failed_collections and len(failed_elements) > 0:
            element_error = "Failed to fetch collection element(s):\n"
            for failed_element in failed_elements:
                element_error += f"\n- {failed_element['error_message']}"
            fetched_target["error_message"] = element_error
            fetched_target["elements"] = None
        else:
            fetched_target["elements"] = elements
    else:
        fetched_target["elements"] = []
        fetched_target["error_message"] = expansion_error
    return fetched_target


def _bagit_to_items(directory):
    bdbag.bdbag_api.resolve_fetch(directory)
    bdbag.bdbag_api.validate_bag(directory)
    items = _directory_to_items(os.path.join(directory, "data"))
    return items


def _decompress_target(upload_config: "UploadConfig", target: Dict[str, Any]):
    elements_from_name, elements_from_path, _ = _has_src_to_path(upload_config, target, is_dataset=False)
    # by default Galaxy will check for a directory with a single file and interpret that
    # as the new root for expansion, this is a good user experience for uploading single
    # files in a archive but not great from an API perspective. Allow disabling by setting
    # fuzzy_root to False to literally interpret the target.
    fuzzy_root = target.get("fuzzy_root", True)
    temp_directory = os.path.abspath(tempfile.mkdtemp(prefix=elements_from_name, dir=upload_config.working_directory))
    with CompressedFile(elements_from_path) as cf:
        result = cf.extract(temp_directory)
    return result if fuzzy_root else temp_directory


def elements_tree_map(f, items):
    new_items = []
    for item in items:
        if "elements" in item:
            new_item = item.copy()
            new_item["elements"] = elements_tree_map(f, item["elements"])
            new_items.append(new_item)
        else:
            new_items.append(f(item))
    return new_items


def _directory_to_items(directory):
    items: List[Dict[str, Any]] = []
    dir_elements: Dict[str, Any] = {}
    for root, dirs, files in os.walk(directory):
        if root in dir_elements:
            target = dir_elements[root]
        else:
            target = items
        for dir in sorted(dirs):
            dir_dict = {"name": dir, "elements": []}
            dir_elements[os.path.join(root, dir)] = dir_dict["elements"]
            target.append(dir_dict)
        for file in sorted(files):
            target.append({"src": "path", "path": os.path.join(root, file)})

    return items


def _has_src_to_name(item) -> Optional[str]:
    # Logic should broadly match logic of _has_src_to_path but not resolve the item
    # into a path.
    name = item.get("name")
    src = item.get("src")
    if src == "url":
        url = item.get("url")
        if name is None:
            name = url.split("/")[-1]
    elif src == "path":
        path = item["path"]
        if name is None:
            name = os.path.basename(path)
    return name


def _has_src_to_path(
    upload_config: "UploadConfig",
    item: Dict[str, Any],
    is_dataset: bool = False,
    link_data_only: bool = False,
    link_data_only_explicitly_set: bool = False,
) -> Tuple[str, str, bool]:
    assert "src" in item, item
    src = item.get("src")
    name = item.get("name")
    is_link = False
    if src == "url":
        url = item.get("url")
        file_sources = ensure_file_sources(upload_config.file_sources)
        assert url, "url cannot be empty"
        if not link_data_only_explicitly_set:
            file_source, rel_path = file_sources.get_file_source_path(url)
            prefer_links = file_source.prefer_links()
            if prefer_links:
                if rel_path.startswith("/"):
                    rel_path = rel_path[1:]
                path = os.path.abspath(os.path.join(file_source.root, rel_path))
                if name is None:
                    name = url.split("/")[-1]
                is_link = True
                return name, path, is_link

        try:
            path = stream_url_to_file(url, file_sources=upload_config.file_sources, dir=upload_config.working_directory)
        except Exception as e:
            raise Exception(f"Failed to fetch url {url}. {str(e)}")

        if not is_dataset:
            # Actual target dataset will validate and put results in dict
            # that gets passed back to Galaxy.
            for hash_function in HASH_NAMES:
                hash_value = item.get(hash_function)
                if hash_value:
                    _handle_hash_validation(hash_function, hash_value, path)
        if name is None:
            name = url.split("/")[-1]
    elif src == "pasted":
        path = stream_to_file(StringIO(item["paste_content"]), dir=upload_config.working_directory)
        if name is None:
            name = "Pasted Entry"
    else:
        assert src == "path"
        path = item["path"]
        if name is None:
            name = os.path.basename(path)
    return name, path, is_link


def _handle_hash_validation(hash_function: HashFunctionNameEnum, hash_value: str, path: str):
    verify_hash(path, hash_func_name=hash_function, hash_value=hash_value, what="upload")


def _arg_parser():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument("--galaxy-root")
    parser.add_argument("--datatypes-registry")
    parser.add_argument("--request-version")
    parser.add_argument("--request")
    parser.add_argument("--working-directory")
    return parser


def get_file_sources(working_directory, file_sources_as_dict=None):
    from galaxy.files import ConfiguredFileSources

    file_sources = None
    if file_sources_as_dict is None:
        file_sources_path = os.path.join(working_directory, "file_sources.json")
        if os.path.exists(file_sources_path):
            file_sources_as_dict = None
            with open(file_sources_path) as f:
                file_sources_as_dict = json.load(f)
    if file_sources_as_dict is not None:
        file_sources = ConfiguredFileSources.from_dict(file_sources_as_dict)
    if file_sources is None:
        ConfiguredFileSources.from_dict(None)
    return file_sources


class UploadConfig:
    def __init__(
        self,
        request: Dict[str, Any],
        registry: Registry,
        working_directory: str,
        allow_failed_collections: bool,
        file_sources_dict: Optional[Dict] = None,
    ):
        self.registry = registry
        self.working_directory = working_directory
        self.allow_failed_collections = allow_failed_collections
        self.check_content = request.get("check_content", True)
        self.to_posix_lines = request.get("to_posix_lines", False)
        self.space_to_tab = request.get("space_to_tab", False)
        self.auto_decompress = request.get("auto_decompress", False)
        self.deferred = request.get("deferred", False)
        self.link_data_only, self.link_data_only_explicit = _link_data_only(request)
        self.file_sources_dict = file_sources_dict
        self._file_sources = None

        self.__workdir = os.path.abspath(working_directory)
        self.__upload_count = 0

    @property
    def file_sources(self):
        if self._file_sources is None:
            self._file_sources = get_file_sources(self.working_directory, file_sources_as_dict=self.file_sources_dict)
        return self._file_sources

    def get_option(self, item, key):
        """Return item[key] if specified otherwise use default from UploadConfig.

        This default represents the default for the whole request instead item which
        is the option for individual files.
        """
        if key in item:
            return item[key]
        else:
            return getattr(self, key)

    def __new_dataset_path(self):
        path = os.path.join(self.working_directory, f"gxupload_{self.__upload_count}")
        self.__upload_count += 1
        return path

    def ensure_in_working_directory(self, path: str, purge_source, in_place) -> str:
        if in_directory(path, self.__workdir):
            return path

        new_path = self.__new_dataset_path()
        if purge_source:
            try:
                shutil.move(path, new_path)
                # Drop .info file if it exists
                try:
                    os.remove(f"{path}.info")
                except FileNotFoundError:
                    pass
            except OSError as e:
                # We may not have permission to remove converted_path
                if e.errno != errno.EACCES:
                    raise
        else:
            shutil.copy(path, new_path)

        return new_path


def _link_data_only(has_config_dict) -> Tuple[bool, bool]:
    if "link_data_only" in has_config_dict:
        link_data_only_raw = has_config_dict["link_data_only"]
        if not isinstance(link_data_only_raw, bool):
            # Allow the older string values of 'copy_files' and 'link_to_files'
            link_data_only = link_data_only_raw == "copy_files"
        else:
            link_data_only = link_data_only_raw
        link_data_only_explicit = True
    else:
        link_data_only = False
        link_data_only_explicit = False
    return link_data_only, link_data_only_explicit


def _for_each_src(f, obj):
    if isinstance(obj, list):
        for item in obj:
            _for_each_src(f, item)
    if isinstance(obj, dict):
        if "src" in obj:
            f(obj)
        for value in obj.values():
            _for_each_src(f, value)


if __name__ == "__main__":
    main()
