import logging
import os

from galaxy.actions.library import (
    validate_path_upload,
    validate_server_directory_upload,
)
from galaxy.exceptions import RequestParameterInvalidException
from galaxy.model.store.discover import (
    get_required_item,
    replace_request_syntax_sugar,
)
from galaxy.tools.actions.upload_common import (
    validate_datatype_extension,
    validate_url,
)
from galaxy.util import relpath

log = logging.getLogger(__name__)

VALID_DESTINATION_TYPES = ["library", "library_folder", "hdca", "hdas"]
# These elements_from cannot be sym linked to because they only exist during upload.
ELEMENTS_FROM_TRANSIENT_TYPES = ["archive", "bagit_archive"]


def validate_and_normalize_targets(trans, payload):
    """Validate and normalize all src references in fetch targets.

    - Normalize ftp_import and server_dir src entries into simple path entries
      with the relevant paths resolved and permissions / configuration checked.
    - Check for file:// URLs in items src of "url" and convert them into path
      src items - after verifying path pastes are allowed and user is admin.
    - Check for valid URLs to be fetched for http and https entries.
    - Based on Galaxy configuration and upload types set purge_source and in_place
      as needed for each upload.
    """
    targets = payload.get("targets", [])

    for target in targets:
        destination = get_required_item(target, "destination", "Each target must specify a 'destination'")
        destination_type = get_required_item(destination, "type", "Each target destination must specify a 'type'")

        if destination_type == "library":
            library_name = get_required_item(destination, "name", "Must specify a library name")
            description = destination.get("description", "")
            synopsis = destination.get("synopsis", "")
            library = trans.app.library_manager.create(trans, library_name, description=description, synopsis=synopsis)
            destination["type"] = "library_folder"
            for key in ["name", "description", "synopsis"]:
                if key in destination:
                    del destination[key]
            destination["library_folder_id"] = trans.app.security.encode_id(library.root_folder.id)

    # Unlike upload.py we don't transmit or use run_as_real_user in the job - we just make sure
    # in_place and purge_source are set on the individual upload fetch sources as needed based
    # on this.
    run_as_real_user = trans.app.config.external_chown_script is not None  # See comment in upload.py
    purge_ftp_source = getattr(trans.app.config, "ftp_upload_purge", True) and not run_as_real_user

    payload["check_content"] = trans.app.config.check_upload_content

    def check_src(item):

        validate_datatype_extension(datatypes_registry=trans.app.datatypes_registry, ext=item.get("ext"))

        # Normalize file:// URLs into paths.
        if item["src"] == "url":
            if "url" not in item:
                raise RequestParameterInvalidException("src specified as 'url' but 'url' not specified")

            url = item["url"]
            if url.startswith("file://"):
                item["src"] = "path"
                item["path"] = url[len("file://") :]
                del item["url"]

        src = item["src"]
        if src == "pasted":
            if item.get("url") is not None:
                raise RequestParameterInvalidException(
                    "Cannot specify a 'url' when fetching data with pasted content 'src'"
                )
            if "paste_content" not in item:
                raise RequestParameterInvalidException("src of type 'pasted' requires paste_content field")
        else:
            if "paste_content" in item:
                raise RequestParameterInvalidException(
                    "'paste_content' field can only be specified with src of type 'pasted'"
                )

        _handle_invalid_link_data_only_elements_type(item)

        if src == "path" or (src == "url" and item["url"].startswith("file:")):
            # Validate is admin, leave alone.
            validate_path_upload(trans)
        elif src == "server_dir":
            # Validate and replace with path definition.
            server_dir = item["server_dir"]
            full_path, _ = validate_server_directory_upload(trans, server_dir)
            item["src"] = "path"
            item["path"] = full_path
        elif src == "ftp_import":
            ftp_path = item["ftp_path"]
            full_path = None

            # It'd be nice if this can be de-duplicated with what is in parameters/grouping.py.
            user_ftp_dir = trans.user_ftp_dir
            is_directory = False

            assert not os.path.islink(user_ftp_dir), "User FTP directory cannot be a symbolic link"
            for (dirpath, dirnames, filenames) in os.walk(user_ftp_dir):
                for filename in filenames:
                    if ftp_path == filename:
                        path = relpath(os.path.join(dirpath, filename), user_ftp_dir)
                        if not os.path.islink(os.path.join(dirpath, filename)):
                            full_path = os.path.abspath(os.path.join(user_ftp_dir, path))
                            break

                for dirname in dirnames:
                    if ftp_path == dirname:
                        path = relpath(os.path.join(dirpath, dirname), user_ftp_dir)
                        if not os.path.islink(os.path.join(dirpath, dirname)):
                            full_path = os.path.abspath(os.path.join(user_ftp_dir, path))
                            is_directory = True
                            break

            if is_directory:
                # If the target is a directory - make sure no files under it are symbolic links
                for (dirpath, dirnames, filenames) in os.walk(full_path):
                    for filename in filenames:
                        if ftp_path == filename:
                            path = relpath(os.path.join(dirpath, filename), full_path)
                            if not os.path.islink(os.path.join(dirpath, filename)):
                                full_path = False
                                break

                    for dirname in dirnames:
                        if ftp_path == dirname:
                            path = relpath(os.path.join(dirpath, filename), full_path)
                            if not os.path.islink(os.path.join(dirpath, filename)):
                                full_path = False
                                break

            if not full_path:
                raise RequestParameterInvalidException(
                    "Failed to find referenced ftp_path or symbolic link was enountered"
                )

            item["src"] = "path"
            item["path"] = full_path
            item["purge_source"] = purge_ftp_source
        elif src == "url":
            url = item["url"]
            looks_like_url = False
            for url_prefix in ["http://", "https://", "ftp://", "ftps://"]:
                if url.startswith(url_prefix):
                    looks_like_url = True
                    break

            if not looks_like_url and trans.app.file_sources.looks_like_uri(url):
                looks_like_url = True

            if not looks_like_url:
                raise RequestParameterInvalidException(f"Invalid URL [{url}] found in src definition.")

            validate_url(url, trans.app.config.fetch_url_allowlist_ips)
            item["in_place"] = run_as_real_user
        elif src == "files":
            item["in_place"] = run_as_real_user

        # Small disagreement with traditional uploads - we purge less by default since whether purging
        # happens varies based on upload options in non-obvious ways.
        # https://github.com/galaxyproject/galaxy/issues/5361
        if "purge_source" not in item:
            item["purge_source"] = False

    replace_request_syntax_sugar(targets)
    _for_each_src(check_src, targets)


def _handle_invalid_link_data_only_elements_type(item):
    link_data_only = item.get("link_data_only", False)
    if link_data_only and item.get("elements_from", False) in ELEMENTS_FROM_TRANSIENT_TYPES:
        raise RequestParameterInvalidException(
            f"link_data_only is invalid for derived elements from [{item.get('elements_from')}]"
        )


def _for_each_src(f, obj):
    if isinstance(obj, list):
        for item in obj:
            _for_each_src(f, item)
    if isinstance(obj, dict):
        if "src" in obj:
            f(obj)
        for value in obj.values():
            _for_each_src(f, value)
