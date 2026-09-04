"""
Galaxy FilesSource implementation for openBIS [1].

openBIS is an ELN-LIMS (Electronic Lab Notebook + Laboratory Information Management System) developed by
ETH Zurich. Data in openBIS is organized in a fixed hierarchy of typed, metadata-carrying entities rather than
a plain file tree:

    Space -> Project -> Experiment (Collection) -> Object (Sample) -> DataSet -> Files

A DataSet is a registered, immutable bundle of files; it can be attached either to an Object or directly to an
Experiment. Separately, openBIS also has AFS ("Atomic File System"): a general-purpose, per-Object (or
per-Experiment) mutable file area with its own list/read/write/delete API. It's what the ELN-LIMS UI's
"Uploads"/"Files" widget on an Object or Experiment page actually stores files in - it is not a DataSet and
is invisible to DataSet-oriented calls (``get_datasets``) or to the classic Attachment API (``get_attachments``).
Both mechanisms are exposed here, since real users' files may live in either one.

This module maps that hierarchy onto virtual, POSIX-like paths so it can be browsed like any other Galaxy file
source:

    /{space}
    /{space}/{project}
    /{space}/{project}/{experiment}
    /{space}/{project}/{experiment}/{object_code}                       (an Object's DataSets, plus its AFS "files" folder)
    /{space}/{project}/{experiment}/{dataset_permId}                    (a DataSet attached directly to the Experiment)
    /{space}/{project}/{experiment}/files                               (the Experiment's own AFS "files" folder)
    /{space}/{project}/{experiment}/{object_code}/{dataset_permId}
    /{space}/{project}/{experiment}/{object_code}/{dataset_permId}/{file/sub/path...}
    /{space}/{project}/{experiment}/{dataset_permId}/{file/sub/path...}
    /{space}/{project}/{experiment}/{object_code}/files/{file/sub/path...}
    /{space}/{project}/{experiment}/files/{file/sub/path...}

Since Object codes, DataSet permIds, and the literal segment ``files`` all share the same path position at the
fourth level, resolving that segment requires a lookup (tried as ``files`` first, then as an Object, then as a
DataSet) rather than being decidable from the path alone. This also means an Object or Experiment whose code
happens to literally be ``files`` is unreachable - an accepted, documented limitation rather than a bug.

This file source is integrated directly with the vendor client library: pyBIS [2], the official Python wrapper
around openBIS's v3 JSON-RPC API and AFS. Authentication uses a Personal Access Token (PAT) rather than a stored
username/password.

Known limitations of this first implementation:

- Recursive listing is not supported.
- Per-file sizes are not available cheaply from pyBIS's ``DataSet.file_list`` (only relative paths are
  returned), so DataSet file entries report a size of 0. AFS file entries do report a real size, since AFS's
  ``list`` call returns it directly.
- Existing DataSets are exposed read-only. openBIS 7 recommends AFS for new files and plans to remove the
  legacy DataSet store in openBIS 8, so all Galaxy uploads and created folders must target an Object's or
  Collection's ``files`` (AFS) folder.
- AFS's ``list`` call returns an empty list both for an empty directory and for a path that doesn't exist at
  all, so browsing into a mistyped AFS sub-path silently shows nothing rather than raising an error.

References:

- [1] https://openbis.ch/
- [2] https://pypi.org/project/PyBIS/
"""

import os
import shutil
import tempfile
from typing import (
    cast,
    TYPE_CHECKING,
)

from galaxy.exceptions import (
    MessageException,
    ObjectNotFound,
)
from galaxy.files.models import (
    AnyRemoteEntry,
    BaseFileSourceConfiguration,
    BaseFileSourceTemplateConfiguration,
    Entry,
    EntryData,
    FilesSourceRuntimeContext,
    RemoteDirectory,
    RemoteFile,
)
from galaxy.files.sources import (
    BaseFilesSource,
    PluginKind,
)
from galaxy.util.config_templates import TemplateExpansion

try:
    from pybis import Openbis
    from pybis.afs.afs_client import AfsClient
except ImportError:
    Openbis = None
    AfsClient = None

if TYPE_CHECKING:
    from pybis.dataset import DataSet
    from pybis.openbis_object import OpenBisObject

__all__ = ("OpenBisFilesSource",)

PACKAGE_MESSAGE = "FilesSource plugin is missing required Python package [pybis]"


class OpenBisFileSourceTemplateConfiguration(BaseFileSourceTemplateConfiguration):
    base_url: str | TemplateExpansion
    token: str | TemplateExpansion
    verify_certificates: bool | TemplateExpansion = True


class OpenBisFileSourceConfiguration(BaseFileSourceConfiguration):
    base_url: str
    token: str
    verify_certificates: bool = True


class OpenBisFilesSource(BaseFilesSource[OpenBisFileSourceTemplateConfiguration, OpenBisFileSourceConfiguration]):
    plugin_type = "openbis"
    plugin_kind = PluginKind.rdm
    supports_pagination = False
    supports_search = False
    supports_sorting = False

    template_config_class = OpenBisFileSourceTemplateConfiguration
    resolved_config_class = OpenBisFileSourceConfiguration

    def __init__(self, template_config: OpenBisFileSourceTemplateConfiguration):
        if Openbis is None:
            raise Exception(PACKAGE_MESSAGE)
        super().__init__(template_config)

    def _get_client(self, config: OpenBisFileSourceConfiguration) -> "Openbis":
        client = Openbis(config.base_url, verify_certificates=config.verify_certificates)
        client.set_token(config.token)
        return client

    def _get_afs_client(self, config: OpenBisFileSourceConfiguration) -> "AfsClient":
        afs_url = f"{config.base_url.rstrip('/')}/afs-server"
        return AfsClient(afs_url, config.token, verify=config.verify_certificates)

    def _list(
        self,
        context: FilesSourceRuntimeContext[OpenBisFileSourceConfiguration],
        path="/",
        recursive=False,
        write_intent: bool = False,
        limit: int | None = None,
        offset: int | None = None,
        query: str | None = None,
        sort_by: str | None = None,
    ) -> tuple[list[AnyRemoteEntry], int]:
        if recursive:
            raise MessageException("Recursive listing is not supported by the openBIS file source.")
        segments = _split_path(path)
        client = self._get_client(context.config)
        try:
            entries = self._list_segments(client, context.config, segments)
        except ObjectNotFound:
            raise
        except Exception as e:
            raise MessageException(f"Problem listing openBIS path '{path}'. Reason: {e}") from e
        entries.sort(key=lambda entry: (entry.class_ != "Directory", entry.name.casefold()))
        return entries, len(entries)

    def _list_segments(
        self, client: "Openbis", config: OpenBisFileSourceConfiguration, segments: list[str]
    ) -> list[AnyRemoteEntry]:
        depth = len(segments)
        if depth == 0:
            return [self._space_entry(space.code) for space in client.get_spaces()]
        if depth == 1:
            (space,) = segments
            return [self._project_entry(space, project.code) for project in client.get_projects(space=space)]
        if depth == 2:
            space, project = segments
            experiments = client.get_experiments(project=f"/{space}/{project}")
            return [self._experiment_entry(space, project, experiment.code) for experiment in experiments]
        if depth == 3:
            space, project, experiment = segments
            experiment_id = f"/{space}/{project}/{experiment}"
            exp = client.get_experiment(experiment_id)
            entries: list[AnyRemoteEntry] = [
                self._object_entry(space, project, experiment, obj.code)
                for obj in client.get_samples(experiment=experiment_id)
            ]
            entries.extend(
                self._dataset_entry(space, project, experiment, None, dataset.permId)
                for dataset in client.get_datasets(experiment=experiment_id)
                # Collection searches also return DataSets owned by their Objects.
                if dataset.sample is None
            )
            entries.append(self._afs_entry(space, project, experiment, None))
            return entries

        space, project, experiment, fourth, *rest = segments

        if fourth == "files":
            exp = client.get_experiment(f"/{space}/{project}/{experiment}")
            return self._list_afs(client, config, space, project, experiment, None, exp.permId, rest)

        experiment_id = f"/{space}/{project}/{experiment}"
        obj = self._try_get_object(client, experiment_id, fourth)
        if obj is not None:
            if not rest:
                entries = [
                    self._dataset_entry(space, project, experiment, fourth, dataset.permId)
                    for dataset in client.get_datasets(sample=obj)
                ]
                entries.append(self._afs_entry(space, project, experiment, fourth))
                return entries
            fifth, *file_or_afs_rest = rest
            if fifth == "files":
                return self._list_afs(client, config, space, project, experiment, fourth, obj.permId, file_or_afs_rest)
            dataset = self._require_dataset(client, fifth, sample=obj)
            return self._list_dataset_files(space, project, experiment, fourth, dataset, file_or_afs_rest)

        dataset = self._require_dataset(client, fourth, experiment_id=experiment_id)
        return self._list_dataset_files(space, project, experiment, None, dataset, rest)

    def _list_afs(
        self,
        client: "Openbis",
        config: OpenBisFileSourceConfiguration,
        space: str,
        project: str,
        experiment: str,
        obj_code: str | None,
        owner_permId: str,
        prefix_parts: list[str],
    ) -> list[AnyRemoteEntry]:
        afs = self._get_afs_client(config)
        source = "/" + "/".join(prefix_parts) if prefix_parts else "/"
        afs_files = afs.list(owner_permId, source, recursively=False)
        base_parts = [space, project, experiment] + ([obj_code] if obj_code else []) + ["files"]
        entries: list[AnyRemoteEntry] = []
        for f in afs_files:
            entry_parts = base_parts + prefix_parts + [f.name]
            entry_path = "/" + "/".join(entry_parts)
            if f.directory:
                entries.append(RemoteDirectory(name=f.name, uri=self.uri_from_path(entry_path), path=entry_path))
            else:
                entries.append(
                    RemoteFile(name=f.name, size=int(f.size), uri=self.uri_from_path(entry_path), path=entry_path)
                )
        return entries

    def _list_dataset_files(
        self,
        space: str,
        project: str,
        experiment: str,
        obj_code: str | None,
        dataset: "DataSet",
        prefix_parts: list[str],
    ) -> list[AnyRemoteEntry]:
        prefix = "/".join(prefix_parts)
        prefix_with_slash = f"{prefix}/" if prefix else ""
        base_parts = [space, project, experiment] + ([obj_code] if obj_code else []) + [dataset.permId]

        children: dict[str, bool] = {}  # name -> is currently known to be a leaf file
        matched = False
        for filepath in dataset.file_list:
            if prefix:
                if filepath == prefix:
                    matched = True
                    continue
                if not filepath.startswith(prefix_with_slash):
                    continue
                remainder = filepath[len(prefix_with_slash) :]
            else:
                remainder = filepath
            matched = True
            name, sep, _ = remainder.partition("/")
            is_leaf = not sep
            children[name] = children.get(name, is_leaf) and is_leaf

        if prefix and not matched:
            raise ObjectNotFound(f"No files found under '{prefix}' in openBIS dataset {dataset.permId}")

        entries: list[AnyRemoteEntry] = []
        for name in sorted(children):
            entry_parts = base_parts + prefix_parts + [name]
            entry_path = "/" + "/".join(entry_parts)
            if children[name]:
                # pyBIS file_list contains paths but no sizes.
                entries.append(RemoteFile(name=name, uri=self.uri_from_path(entry_path), path=entry_path, size=0))
            else:
                entries.append(RemoteDirectory(name=name, uri=self.uri_from_path(entry_path), path=entry_path))
        return entries

    def _space_entry(self, space_code: str) -> RemoteDirectory:
        path = f"/{space_code}"
        return RemoteDirectory(name=space_code, uri=self.uri_from_path(path), path=path)

    def _project_entry(self, space: str, project_code: str) -> RemoteDirectory:
        path = f"/{space}/{project_code}"
        return RemoteDirectory(name=project_code, uri=self.uri_from_path(path), path=path)

    def _experiment_entry(self, space: str, project: str, experiment_code: str) -> RemoteDirectory:
        path = f"/{space}/{project}/{experiment_code}"
        return RemoteDirectory(name=experiment_code, uri=self.uri_from_path(path), path=path)

    def _object_entry(self, space: str, project: str, experiment: str, object_code: str) -> RemoteDirectory:
        path = f"/{space}/{project}/{experiment}/{object_code}"
        return RemoteDirectory(name=object_code, uri=self.uri_from_path(path), path=path)

    def _dataset_entry(
        self, space: str, project: str, experiment: str, obj_code: str | None, dataset_permId: str
    ) -> RemoteDirectory:
        parts = [space, project, experiment] + ([obj_code] if obj_code else []) + [dataset_permId]
        path = "/" + "/".join(parts)
        return RemoteDirectory(name=dataset_permId, uri=self.uri_from_path(path), path=path)

    def _afs_entry(self, space: str, project: str, experiment: str, obj_code: str | None) -> RemoteDirectory:
        parts = [space, project, experiment] + ([obj_code] if obj_code else []) + ["files"]
        path = "/" + "/".join(parts)
        return RemoteDirectory(name="files", uri=self.uri_from_path(path), path=path)

    def _create_entry(
        self, entry_data: EntryData, context: FilesSourceRuntimeContext[OpenBisFileSourceConfiguration]
    ) -> Entry:
        """Create an AFS folder."""
        # CreateEntryPayload supplies target at runtime, but the base API types this as EntryData.
        target = getattr(entry_data, "target", None)
        if not target:
            raise MessageException("Cannot create a folder without a target location.")
        target_path = self.to_relative_path(target)
        segments = _split_path(target_path)
        name_segments = _split_path(entry_data.name)
        if len(name_segments) != 1:
            raise MessageException("An openBIS AFS folder name must be a single path component.")
        entry_name = name_segments[0]
        client = self._get_client(context.config)

        afs_target = self._try_resolve_afs(client, segments)
        if afs_target is not None:
            owner_permId, path_parts = afs_target
            base_parts = segments[: len(segments) - len(path_parts)]
        elif len(segments) == 3:
            experiment_id = "/" + "/".join(segments)
            exp = client.get_experiment(experiment_id)
            owner_permId = exp.permId
            path_parts = []
            base_parts = [*segments, "files"]
        elif len(segments) == 4:
            space, project, experiment, object_code = segments
            experiment_id = f"/{space}/{project}/{experiment}"
            obj = self._try_get_object(client, experiment_id, object_code)
            if obj is None:
                # A direct Collection DataSet occupies the same position as an Object.
                if self._try_get_dataset(client, object_code) is not None:
                    raise MessageException(
                        f"'{object_code}' is an existing openBIS DataSet. DataSets can't contain "
                        "folders -- create the new folder in the Collection's 'files' folder instead."
                    )
                raise ObjectNotFound(f"Object '{object_code}' not found in openBIS")
            owner_permId = obj.permId
            path_parts = []
            base_parts = [*segments, "files"]
        else:
            # At depth five the target may be a DataSet beneath an Object.
            if len(segments) == 5 and self._try_get_dataset(client, segments[-1]) is not None:
                raise MessageException(
                    f"'{segments[-1]}' is an existing openBIS DataSet. DataSets can't contain "
                    "folders -- create the new folder in the Collection or Object's 'files' "
                    "folder instead."
                )
            raise MessageException(
                "New folders can only be created directly under an openBIS Collection, an "
                "Object, or inside an existing 'files' (AFS) folder."
            )

        afs = self._get_afs_client(context.config)
        new_folder_parts = [*path_parts, entry_name]
        afs.create(owner_permId, "/" + "/".join(new_folder_parts), is_directory=True)

        entry_path = "/" + "/".join(base_parts + new_folder_parts)
        return Entry(name=entry_name, uri=self.uri_from_path(entry_path), external_link=None)

    def _try_get_object(self, client: "Openbis", experiment_id: str, code: str) -> "OpenBisObject | None":
        """Find an Object only when it belongs to the Collection encoded in the path."""
        matches = list(client.get_samples(experiment=experiment_id, code=code))
        return matches[0] if matches else None

    def _require_dataset(
        self,
        client: "Openbis",
        code: str,
        *,
        experiment_id: str | None = None,
        sample: "OpenBisObject | None" = None,
    ) -> "DataSet":
        """Find a DataSet only beneath the Collection or Object encoded in the path."""
        if sample is not None:
            matches = client.get_datasets(sample=sample, permId=code)
        elif experiment_id is not None:
            # Collection searches include Object-owned DataSets.
            matches = (
                dataset
                for dataset in client.get_datasets(experiment=experiment_id, permId=code)
                if dataset.sample is None
            )
        else:
            raise ValueError("A DataSet owner is required")
        dataset = next(iter(matches), None)
        if dataset is None:
            raise ObjectNotFound(f"DataSet '{code}' was not found at this openBIS location")
        return dataset

    def _try_get_dataset(self, client: "Openbis", code: str) -> "DataSet | None":
        try:
            return client.get_dataset(code)
        except Exception:
            return None

    def _try_resolve_afs(self, client: "Openbis", segments: list[str]) -> tuple[str, list[str]] | None:
        """Return the AFS owner and path when segments contain an AFS ``files`` root."""
        if len(segments) < 4:
            return None
        space, project, experiment, fourth, *rest = segments
        if fourth == "files":
            exp = client.get_experiment(f"/{space}/{project}/{experiment}")
            return exp.permId, rest
        if rest and rest[0] == "files":
            obj = self._try_get_object(client, f"/{space}/{project}/{experiment}", fourth)
            if obj is not None:
                return obj.permId, rest[1:]
        return None

    def _resolve_file(
        self, client: "Openbis", source_path: str
    ) -> tuple[str, str, list[str]] | tuple[str, "DataSet", str]:
        segments = _split_path(source_path)

        afs_target = self._try_resolve_afs(client, segments)
        if afs_target is not None:
            owner_permId, path_parts = afs_target
            if not path_parts:
                raise MessageException(f"'{source_path}' does not refer to a file in openBIS.")
            return "afs", owner_permId, path_parts

        if len(segments) < 5:
            raise MessageException(f"'{source_path}' does not refer to a file in openBIS.")
        space, project, experiment, fourth, *rest = segments
        experiment_id = f"/{space}/{project}/{experiment}"
        obj = self._try_get_object(client, experiment_id, fourth)
        if obj is not None:
            if not rest:
                raise MessageException(f"'{source_path}' does not refer to a file in openBIS.")
            dataset_code, *file_parts = rest
        else:
            dataset_code, file_parts = fourth, rest
        dataset = self._require_dataset(
            client,
            dataset_code,
            sample=obj if obj is not None else None,
            experiment_id=None if obj is not None else experiment_id,
        )
        relative_file_path = "/".join(file_parts)
        if relative_file_path not in dataset.file_list:
            raise ObjectNotFound(f"'{relative_file_path}' not found in openBIS dataset {dataset.permId}")
        return "dataset", dataset, relative_file_path

    def _realize_to(
        self,
        source_path: str,
        native_path: str,
        context: FilesSourceRuntimeContext[OpenBisFileSourceConfiguration],
    ):
        client = self._get_client(context.config)
        kind, owner_or_dataset, payload = self._resolve_file(client, source_path)

        if kind == "afs":
            owner_permId = owner_or_dataset
            path_parts = payload
            afs = self._get_afs_client(context.config)
            source = "/" + "/".join(path_parts)
            with tempfile.TemporaryDirectory() as tmp_dir:
                afs.download_files(owner_permId, source, tmp_dir, wait_until_finished=True)
                # download_files preserves the full AFS-relative path.
                downloaded_path = os.path.join(tmp_dir, *path_parts)
                shutil.move(downloaded_path, native_path)
            return

        dataset = cast("DataSet", owner_or_dataset)
        relative_file_path = cast(str, payload)
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Default folders make the download location match dataset.file_list.
            dataset.download(
                files=[relative_file_path],
                destination=tmp_dir,
                create_default_folders=True,
                wait_until_finished=True,
            )
            downloaded_path = os.path.join(tmp_dir, dataset.permId, relative_file_path)
            shutil.move(downloaded_path, native_path)

    def _write_afs(
        self,
        config: OpenBisFileSourceConfiguration,
        base_parts: list[str],
        owner_permId: str,
        path_parts: list[str],
        native_path: str,
    ) -> str:
        *dir_parts, filename = path_parts
        afs_dir = "/" + "/".join(dir_parts) if dir_parts else "/"
        afs = self._get_afs_client(config)

        # AFS uses the local basename as the remote filename.
        tmp_dir = None
        upload_path = native_path
        if os.path.basename(native_path) != filename:
            tmp_dir = tempfile.mkdtemp()
            upload_path = os.path.join(tmp_dir, filename)
            shutil.copyfile(native_path, upload_path)
        try:
            afs.upload_files(owner_permId, afs_dir, [upload_path], wait_until_finished=True)
        finally:
            if tmp_dir:
                shutil.rmtree(tmp_dir, ignore_errors=True)

        return "/" + "/".join(base_parts + path_parts)

    def _write_from(
        self,
        target_path: str,
        native_path: str,
        context: FilesSourceRuntimeContext[OpenBisFileSourceConfiguration],
    ) -> str:
        segments = _split_path(target_path)
        if len(segments) < 5:
            raise MessageException("Files can only be uploaded inside a Collection's or Object's 'files' (AFS) folder.")
        client = self._get_client(context.config)

        afs_target = self._try_resolve_afs(client, segments)
        if afs_target is not None:
            owner_permId, path_parts = afs_target
            if not path_parts:
                raise MessageException("Specify a filename to upload within the 'files' folder.")
            base_parts = segments[: len(segments) - len(path_parts)]
            return self._write_afs(context.config, base_parts, owner_permId, path_parts, native_path)

        # Existing DataSets remain browseable and downloadable, but all new writes use AFS.
        candidate_segments = segments[:-1]
        if len(candidate_segments) in (4, 5) and self._try_get_dataset(client, candidate_segments[-1]) is not None:
            raise MessageException(
                f"'{candidate_segments[-1]}' is an existing openBIS DataSet. DataSets are immutable "
                "and are exposed read-only. Export to the Collection's or Object's 'files' (AFS) folder instead."
            )

        raise MessageException(
            "Files can only be uploaded inside a Collection's or Object's 'files' (AFS) folder. "
            "Existing openBIS DataSets are available for browsing and download only."
        )


def _split_path(path: str) -> list[str]:
    segments = [segment for segment in (path or "/").strip("/").split("/") if segment]
    if any(segment in {".", ".."} for segment in segments):
        raise MessageException("Relative path components '.' and '..' are not allowed in openBIS paths.")
    return segments
