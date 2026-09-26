"""
Galaxy FilesSource implementation for openBIS [1].

openBIS is an ELN-LIMS (Electronic Lab Notebook + Laboratory Information Management System) developed by
ETH Zurich. This plugin exposes the Collection-based part of openBIS's entity model as a virtual hierarchy
rather than a plain file tree (Experiment and Sample are API names for Collection and Object):

    Space -> Project -> Collection -> [Object] -> DataSet -> Files
                                             -> AFS files

A physical DataSet is a registered bundle whose file contents are immutable; it can belong to an Object or
directly to a Collection. Its metadata can still be updated. Separately, AFS ("Atomic File System") provides
mutable files owned by Collections or Objects. The openBIS 7 ELN-LIMS Files tab uses AFS, a separate API from
legacy DataSets and classic Attachments. This plugin browses and downloads legacy DataSet files and provides
listing, downloads, uploads and folder creation for AFS. It does not expose AFS rename or delete operations.
The root lists all Spaces visible to the configured PAT, including shared settings Spaces such as
ELN_SETTINGS when accessible; it is not restricted to the user's home Space.

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
DataSet) rather than being decidable from the path alone. An Object whose code is literally ``files`` is
therefore unreachable through these paths; a Collection named ``files`` is valid at the third level.
The shared resolver checks Object and DataSet ownership against the parents encoded in the path.

This file source is integrated directly with the vendor client library: pyBIS [2], the official Python wrapper
around openBIS's v3 JSON-RPC API and AFS. Authentication uses a Personal Access Token (PAT) rather than a stored
username/password.

Known limitations of this first implementation:

- Recursive listing, pagination and server-side search/sorting are not supported; entries are sorted locally.
- Objects outside Collections, classic Attachments and linked/container DataSets have no dedicated traversal.
- Per-file sizes are not available cheaply from pyBIS's ``DataSet.file_list`` (only relative paths are
  returned), so DataSet file entries report a size of 0. AFS file entries do report a real size, since AFS's
  ``list`` call returns it directly.
- Existing DataSets are exposed read-only. openBIS 7 recommends AFS for new files and plans to remove the
  legacy DataSet store in openBIS 8 [3]. Uploads and folder creation both require selecting an existing
  Collection's or Object's ``files`` (AFS) directory; they never create openBIS entities.
- The pinned pyBIS AFS client can return an empty list for a missing directory as well as an empty one,
  so browsing a mistyped AFS directory may show no entries instead of reporting a missing path.

References:

- [1] https://openbis.ch/
- [2] https://pypi.org/project/PyBIS/
- [3] https://openbis.readthedocs.io/en/7.x/user-documentation/general-users/data-upload.html
"""

import os
import shutil
import tempfile
from dataclasses import dataclass
from typing import TYPE_CHECKING

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


@dataclass
class AfsPath:
    owner_id: str
    base_parts: list[str]
    relative_parts: list[str]


@dataclass
class DatasetPath:
    dataset: "DataSet"
    object_code: str | None
    relative_parts: list[str]


@dataclass
class ObjectPath:
    obj: "OpenBisObject"


WRITE_LOCATION_MESSAGE = (
    "Uploads and folder creation require a Collection's or Object's 'files' (AFS) folder. "
    "DataSets are immutable and exposed read-only."
)


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
            client.get_experiment(experiment_id)  # Validate the Collection even when it has no children.
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

        space, project, experiment = segments[:3]
        resolved = self._resolve_path(client, segments)
        if isinstance(resolved, AfsPath):
            return self._list_afs(
                config,
                resolved,
            )
        if isinstance(resolved, ObjectPath):
            entries = [
                self._dataset_entry(space, project, experiment, segments[3], dataset.permId)
                for dataset in client.get_datasets(sample=resolved.obj)
            ]
            entries.append(self._afs_entry(space, project, experiment, segments[3]))
            return entries
        if isinstance(resolved, DatasetPath):
            return self._list_dataset_files(
                space, project, experiment, resolved.object_code, resolved.dataset, resolved.relative_parts
            )
        raise ObjectNotFound("No entity found at this openBIS location")

    def _list_afs(
        self,
        config: OpenBisFileSourceConfiguration,
        resolved: AfsPath,
    ) -> list[AnyRemoteEntry]:
        afs = self._get_afs_client(config)
        prefix_parts = resolved.relative_parts
        source = "/" + "/".join(prefix_parts) if prefix_parts else "/"
        afs_files = afs.list(resolved.owner_id, source, recursively=False)
        base_parts = resolved.base_parts
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
        entry_name = entry_data.name
        if not entry_name or "/" in entry_name or entry_name in {".", ".."}:
            raise MessageException("An openBIS AFS folder name must be a single path component.")
        client = self._get_client(context.config)
        resolved = self._require_afs(self._resolve_path(client, segments))
        new_folder_parts = [*resolved.relative_parts, entry_name]
        afs = self._get_afs_client(context.config)
        afs.create(resolved.owner_id, "/" + "/".join(new_folder_parts), is_directory=True)
        entry_path = "/" + "/".join(resolved.base_parts + new_folder_parts)
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

    def _resolve_path(self, client: "Openbis", segments: list[str]) -> AfsPath | DatasetPath | ObjectPath | None:
        """Resolve ownership consistently for browsing, downloads and writes."""
        if len(segments) < 4:
            return None
        space, project, collection, fourth, *rest = segments
        collection_id = f"/{space}/{project}/{collection}"
        if fourth == "files":
            collection_obj = client.get_experiment(collection_id)
            return AfsPath(collection_obj.permId, segments[:4], rest)
        obj = self._try_get_object(client, collection_id, fourth)
        if obj is not None:
            if not rest:
                return ObjectPath(obj)
            if rest[0] == "files":
                return AfsPath(obj.permId, segments[:5], rest[1:])
            return DatasetPath(self._require_dataset(client, rest[0], sample=obj), fourth, rest[1:])
        return DatasetPath(self._require_dataset(client, fourth, experiment_id=collection_id), None, rest)

    def _require_afs(self, resolved: AfsPath | DatasetPath | ObjectPath | None) -> AfsPath:
        if not isinstance(resolved, AfsPath):
            raise MessageException(WRITE_LOCATION_MESSAGE)
        return resolved

    def _resolve_file(self, client: "Openbis", source_path: str) -> AfsPath | DatasetPath:
        resolved = self._resolve_path(client, _split_path(source_path))
        if not isinstance(resolved, (AfsPath, DatasetPath)) or not resolved.relative_parts:
            raise MessageException(f"'{source_path}' does not refer to a file in openBIS.")
        if isinstance(resolved, DatasetPath):
            relative_path = "/".join(resolved.relative_parts)
            if relative_path not in resolved.dataset.file_list:
                raise ObjectNotFound(f"'{relative_path}' not found in openBIS dataset {resolved.dataset.permId}")
        return resolved

    def _realize_to(
        self,
        source_path: str,
        native_path: str,
        context: FilesSourceRuntimeContext[OpenBisFileSourceConfiguration],
    ):
        client = self._get_client(context.config)
        resolved = self._resolve_file(client, source_path)

        if isinstance(resolved, AfsPath):
            owner_permId = resolved.owner_id
            path_parts = resolved.relative_parts
            afs = self._get_afs_client(context.config)
            source = "/" + "/".join(path_parts)
            with tempfile.TemporaryDirectory() as tmp_dir:
                afs.download_files(owner_permId, source, tmp_dir, wait_until_finished=True)
                # download_files preserves the full AFS-relative path.
                downloaded_path = os.path.join(tmp_dir, *path_parts)
                shutil.move(downloaded_path, native_path)
            return

        dataset = resolved.dataset
        relative_file_path = "/".join(resolved.relative_parts)
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
            raise MessageException(WRITE_LOCATION_MESSAGE)
        client = self._get_client(context.config)
        # Resolve the parent so a new filename is never mistaken for an entity code.
        parent = self._require_afs(self._resolve_path(client, segments[:-1]))
        return self._write_afs(
            context.config,
            parent.base_parts,
            parent.owner_id,
            [*parent.relative_parts, segments[-1]],
            native_path,
        )


def _split_path(path: str) -> list[str]:
    segments = [segment for segment in (path or "/").strip("/").split("/") if segment]
    if any(segment in {".", ".."} for segment in segments):
        raise MessageException("Relative path components '.' and '..' are not allowed in openBIS paths.")
    return segments
