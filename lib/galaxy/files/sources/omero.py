from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import (
    Optional,
    Union,
)

import tifffile

from galaxy.exceptions import (
    AuthenticationFailed,
    ObjectNotFound,
)
from galaxy.files.models import (
    AnyRemoteEntry,
    BaseFileSourceConfiguration,
    BaseFileSourceTemplateConfiguration,
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
    import omero.sys
    from omero.gateway import BlitzGateway
except ImportError:
    omero = None
    BlitzGateway = None


class OmeroFileSourceTemplateConfiguration(BaseFileSourceTemplateConfiguration):
    username: Union[str, TemplateExpansion]
    password: Union[str, TemplateExpansion]
    host: Union[str, TemplateExpansion]
    port: Union[int, TemplateExpansion]


class OmeroFileSourceConfiguration(BaseFileSourceConfiguration):
    username: str
    password: str
    host: str
    port: int


class OmeroFileSource(BaseFilesSource[OmeroFileSourceTemplateConfiguration, OmeroFileSourceConfiguration]):
    plugin_type = "omero"
    plugin_kind = PluginKind.rfs
    supports_pagination = True
    supports_search = True
    required_module = BlitzGateway
    required_package = "omero-py (requires manual Zeroc IcePy installation)"

    template_config_class = OmeroFileSourceTemplateConfiguration
    resolved_config_class = OmeroFileSourceConfiguration

    def __init__(self, template_config: OmeroFileSourceTemplateConfiguration):
        if self.required_module is None:
            raise self.required_package_exception
        super().__init__(template_config)

    @property
    def required_package_exception(self) -> Exception:
        return Exception(
            f"The Python package '{self.required_package}' is required to use this file source plugin. "
            "Please see https://omero.readthedocs.io/en/stable/developers/Python.html for installation instructions."
        )

    @contextmanager
    def _connection(self, context: FilesSourceRuntimeContext[OmeroFileSourceConfiguration]) -> Iterator[BlitzGateway]:
        """Context manager for OMERO connections with automatic cleanup.

        Establishes a connection to the OMERO server, enables keepalive for long-running
        operations, and ensures proper cleanup on exit.
        """
        if BlitzGateway is None:
            raise self.required_package_exception

        conn = BlitzGateway(
            username=context.config.username,
            passwd=context.config.password,
            host=context.config.host,
            port=context.config.port,
            secure=True,
        )
        if not conn.connect():
            raise AuthenticationFailed(
                f"Could not connect to OMERO server at {context.config.host}:{context.config.port}. "
                "Please verify your credentials and server address."
            )

        try:
            conn.c.enableKeepAlive(60)
            yield conn
        finally:
            conn.close()

    def _list(
        self,
        context: FilesSourceRuntimeContext[OmeroFileSourceConfiguration],
        path="/",
        recursive=False,
        write_intent: bool = False,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        query: Optional[str] = None,
        sort_by: Optional[str] = None,
    ) -> tuple[list[AnyRemoteEntry], int]:
        """
        List OMERO objects in a hierarchical structure:
        - Projects as directories at root level
        - Datasets as directories within projects
        - Images as files within datasets

        Path format:
        - "/" or "" - lists all projects
        - "/project_<id>" - lists datasets in a project
        - "/project_<id>/dataset_<id>" - lists images in a dataset
        """
        with self._connection(context) as omero:
            path_parts = self._parse_path(path)
            results = self._list_entries_for_path(omero, path_parts, limit=limit, offset=offset, query=query)
            total_count = self._count_entries_for_path(omero, path_parts, query=query)
            return results, total_count

    def _parse_path(self, path: str) -> list[str]:
        """Parse and normalize the path into components."""
        return [p for p in path.strip("/").split("/") if p]

    def _list_entries_for_path(
        self,
        omero: BlitzGateway,
        path_parts: list[str],
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        query: Optional[str] = None,
    ) -> list[AnyRemoteEntry]:
        """List entries based on the path depth."""
        if len(path_parts) == 0:
            return self._list_projects(omero, limit=limit, offset=offset, query=query)
        elif len(path_parts) == 1:
            return self._list_datasets(omero, path_parts[0], limit=limit, offset=offset, query=query)
        elif len(path_parts) == 2:
            return self._list_images(omero, path_parts[0], path_parts[1], limit=limit, offset=offset, query=query)
        return []

    def _count_entries_for_path(self, omero: BlitzGateway, path_parts: list[str], query: Optional[str] = None) -> int:
        """Count total entries for pagination without loading all objects."""
        if len(path_parts) == 0:
            return self._count_projects(omero, query=query)
        elif len(path_parts) == 1:
            return self._count_datasets(omero, path_parts[0], query=query)
        elif len(path_parts) == 2:
            return self._count_images(omero, path_parts[1], query=query)
        return 0

    def _count_projects(self, conn: BlitzGateway, query: Optional[str] = None) -> int:
        """Count all projects using efficient HQL query."""
        query_service = conn.getQueryService()
        params = omero.sys.ParametersI()
        hql = "select count(p) from Project p"
        if query:
            hql += " where lower(p.name) like :query"
            params.addString("query", f"%{query.lower()}%")
        result = query_service.projection(hql, params, conn.SERVICE_OPTS)
        return result[0][0].val if result else 0

    def _count_datasets(self, conn: BlitzGateway, project_id_str: str, query: Optional[str] = None) -> int:
        """Count datasets in a project using efficient HQL query."""
        if not project_id_str.startswith("project_"):
            return 0
        project_id = self._extract_id(project_id_str, "project_")
        query_service = conn.getQueryService()
        params = omero.sys.ParametersI()
        params.addId(project_id)
        hql = (
            "select count(d) from Dataset d "
            "where d.id in (select link.child.id from ProjectDatasetLink link where link.parent.id = :id)"
        )
        if query:
            hql += " and lower(d.name) like :query"
            params.addString("query", f"%{query.lower()}%")
        result = query_service.projection(hql, params, conn.SERVICE_OPTS)
        return result[0][0].val if result else 0

    def _count_images(self, conn: BlitzGateway, dataset_id_str: str, query: Optional[str] = None) -> int:
        """Count images in a dataset using efficient HQL query."""
        if not dataset_id_str.startswith("dataset_"):
            return 0
        dataset_id = self._extract_id(dataset_id_str, "dataset_")
        query_service = conn.getQueryService()
        params = omero.sys.ParametersI()
        params.addId(dataset_id)
        hql = (
            "select count(i) from Image i "
            "where i.id in (select link.child.id from DatasetImageLink link where link.parent.id = :id)"
        )
        if query:
            hql += " and lower(i.name) like :query"
            params.addString("query", f"%{query.lower()}%")
        result = query_service.projection(hql, params, conn.SERVICE_OPTS)
        return result[0][0].val if result else 0

    def _list_projects(
        self,
        conn: BlitzGateway,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        query: Optional[str] = None,
    ) -> list[AnyRemoteEntry]:
        """List all projects as directories at root level."""
        if query:
            # Use HQL for server-side filtering with pagination
            return self._list_projects_with_query(conn, query, limit, offset)

        opts = self._build_pagination_opts(limit, offset)
        results: list[AnyRemoteEntry] = []
        for project in conn.getObjects("Project", opts=opts):
            name = project.getName() or f"Project {project.getId()}"
            project_path = f"project_{project.getId()}"
            results.append(
                RemoteDirectory(
                    name=name,
                    uri=self.uri_from_path(project_path),
                    path=project_path,
                )
            )
        return results

    def _list_projects_with_query(
        self,
        conn: BlitzGateway,
        query: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list[AnyRemoteEntry]:
        """List projects matching query using HQL for server-side filtering."""
        query_service = conn.getQueryService()
        params = omero.sys.ParametersI()
        params.addString("query", f"%{query.lower()}%")
        if limit is not None:
            params.page(offset or 0, limit)
        hql = "select p from Project p where lower(p.name) like :query order by p.name"
        projects = query_service.findAllByQuery(hql, params, conn.SERVICE_OPTS)

        results: list[AnyRemoteEntry] = []
        for project in projects:
            project_id = project.getId().getValue()
            name = project.getName().getValue() if project.getName() else f"Project {project_id}"
            project_path = f"project_{project_id}"
            results.append(
                RemoteDirectory(
                    name=name,
                    uri=self.uri_from_path(project_path),
                    path=project_path,
                )
            )
        return results

    def _list_datasets(
        self,
        conn: BlitzGateway,
        project_id_str: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        query: Optional[str] = None,
    ) -> list[AnyRemoteEntry]:
        """List datasets within a project."""
        if not project_id_str.startswith("project_"):
            return []

        project_id = self._extract_id(project_id_str, "project_")

        if query:
            # Use HQL for server-side filtering with pagination
            return self._list_datasets_with_query(conn, project_id_str, project_id, query, limit, offset)

        project = conn.getObject("Project", project_id)
        if not project:
            return []

        results: list[AnyRemoteEntry] = []
        children = list(project.listChildren())
        start = offset or 0
        end = start + limit if limit else None
        for dataset in children[start:end]:
            dataset_path = f"{project_id_str}/dataset_{dataset.getId()}"
            results.append(
                RemoteDirectory(
                    name=dataset.getName() or f"Dataset {dataset.getId()}",
                    uri=self.uri_from_path(dataset_path),
                    path=dataset_path,
                )
            )
        return results

    def _list_datasets_with_query(
        self,
        conn: BlitzGateway,
        project_id_str: str,
        project_id: int,
        query: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list[AnyRemoteEntry]:
        """List datasets matching query using HQL for server-side filtering."""
        query_service = conn.getQueryService()
        params = omero.sys.ParametersI()
        params.addId(project_id)
        params.addString("query", f"%{query.lower()}%")
        if limit is not None:
            params.page(offset or 0, limit)
        hql = (
            "select d from Dataset d "
            "where d.id in (select link.child.id from ProjectDatasetLink link where link.parent.id = :id) "
            "and lower(d.name) like :query order by d.name"
        )
        datasets = query_service.findAllByQuery(hql, params, conn.SERVICE_OPTS)

        results: list[AnyRemoteEntry] = []
        for dataset in datasets:
            dataset_id = dataset.getId().getValue()
            name = dataset.getName().getValue() if dataset.getName() else f"Dataset {dataset_id}"
            dataset_path = f"{project_id_str}/dataset_{dataset_id}"
            results.append(
                RemoteDirectory(
                    name=name,
                    uri=self.uri_from_path(dataset_path),
                    path=dataset_path,
                )
            )
        return results

    def _list_images(
        self,
        conn: BlitzGateway,
        project_id_str: str,
        dataset_id_str: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        query: Optional[str] = None,
    ) -> list[AnyRemoteEntry]:
        """List images within a dataset."""
        if not dataset_id_str.startswith("dataset_"):
            return []

        dataset_id = self._extract_id(dataset_id_str, "dataset_")

        if query:
            # Use HQL for server-side filtering with pagination
            return self._list_images_with_query(conn, project_id_str, dataset_id_str, dataset_id, query, limit, offset)

        dataset = conn.getObject("Dataset", dataset_id)
        if not dataset:
            return []

        results: list[AnyRemoteEntry] = []
        children = list(dataset.listChildren())
        start = offset or 0
        end = start + limit if limit else None
        for image in children[start:end]:
            image_path = f"{project_id_str}/{dataset_id_str}/image_{image.getId()}"
            results.append(self._create_remote_file_for_image(image, image_path))
        return results

    def _list_images_with_query(
        self,
        conn: BlitzGateway,
        project_id_str: str,
        dataset_id_str: str,
        dataset_id: int,
        query: str,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> list[AnyRemoteEntry]:
        """List images matching query using HQL for server-side filtering."""
        query_service = conn.getQueryService()
        params = omero.sys.ParametersI()
        params.addId(dataset_id)
        params.addString("query", f"%{query.lower()}%")
        if limit is not None:
            params.page(offset or 0, limit)
        hql = (
            "select i from Image i "
            "where i.id in (select link.child.id from DatasetImageLink link where link.parent.id = :id) "
            "and lower(i.name) like :query order by i.name"
        )
        image_ids = [img.getId().getValue() for img in query_service.findAllByQuery(hql, params, conn.SERVICE_OPTS)]

        # Use getObjects to get full ImageWrapper objects for metadata
        results: list[AnyRemoteEntry] = []
        for image in conn.getObjects("Image", image_ids):
            image_path = f"{project_id_str}/{dataset_id_str}/image_{image.getId()}"
            results.append(self._create_remote_file_for_image(image, image_path))
        return results

    def _build_pagination_opts(self, limit: Optional[int] = None, offset: Optional[int] = None) -> dict[str, int]:
        """Build OMERO pagination options dictionary."""
        opts: dict[str, int] = {}
        if limit is not None:
            opts["limit"] = limit
        if offset is not None:
            opts["offset"] = offset
        return opts

    def _create_remote_file_for_image(self, image, image_path: str) -> RemoteFile:
        """Create a RemoteFile entry for an OMERO image."""
        ctime = image.getDate()
        ctime_str = ctime.isoformat() if ctime else datetime.now().isoformat()

        estimated_size = self._estimate_image_size(image)

        return RemoteFile(
            name=image.getName() or f"Image {image.getId()}",
            size=estimated_size,
            ctime=ctime_str,
            uri=self.uri_from_path(image_path),
            path=image_path,
        )

    def _estimate_image_size(self, image) -> int:
        """Estimate the size of an OMERO image based on pixel dimensions and type."""
        pixels = image.getPrimaryPixels()
        dimensions = (
            pixels.getSizeX(),
            pixels.getSizeY(),
            pixels.getSizeZ(),
            pixels.getSizeC(),
            pixels.getSizeT(),
        )
        pixel_type = pixels.getPixelsType().getValue()
        bytes_per_pixel = self._get_bytes_per_pixel(pixel_type)

        total_pixels = 1
        for dim in dimensions:
            total_pixels *= dim

        return total_pixels * bytes_per_pixel

    def _get_bytes_per_pixel(self, pixel_type: str) -> int:
        """Determine bytes per pixel based on pixel type."""
        if "int16" in pixel_type or "uint16" in pixel_type:
            return 2
        elif "int32" in pixel_type or "uint32" in pixel_type or "float" in pixel_type:
            return 4
        elif "double" in pixel_type:
            return 8
        return 1

    def _extract_id(self, id_str: str, prefix: str) -> int:
        """Extract numeric ID from a prefixed string."""
        return int(id_str.replace(prefix, ""))

    def _realize_to(
        self, source_path: str, native_path: str, context: FilesSourceRuntimeContext[OmeroFileSourceConfiguration]
    ):
        """
        Download an OMERO image to a local file.

        This method attempts to download the original imported file to preserve
        the original format. If the original file is not available, it falls back
        to exporting pixel data.

        The source_path should be in format: project_<id>/dataset_<id>/image_<id>
        """
        with self._connection(context) as omero:
            image = self._get_image_from_path(omero, source_path)
            self._download_image(image, native_path)

    def _get_image_from_path(self, omero: BlitzGateway, source_path: str):
        """Extract and retrieve an OMERO image from a path."""
        path_parts = self._parse_path(source_path)

        if len(path_parts) != 3 or not path_parts[2].startswith("image_"):
            raise ValueError(
                f"Invalid image path: {source_path}. Expected format: project_<id>/dataset_<id>/image_<id>"
            )

        image_id = self._extract_id(path_parts[2], "image_")
        image = omero.getObject("Image", image_id)

        if not image:
            raise ObjectNotFound(f"Image with ID {image_id} not found in OMERO server")

        return image

    def _download_image(self, image, native_path: str):
        """Download an OMERO image using the best available method."""
        if self._try_download_original_file(image, native_path):
            return

        self._export_as_tiff(image, native_path)

    def _try_download_original_file(self, image, native_path: str) -> bool:
        """Attempt to download the original imported file. Returns True if successful.

        Some OMERO servers (like IDR) restrict downloads of original files.
        In such cases, this method catches the SecurityViolation and returns False
        to allow fallback to pixel data export.
        """
        try:
            if image.countFilesetFiles() == 0:
                return False

            for orig_file in image.getImportedImageFiles():
                self._write_file_in_chunks(orig_file, native_path)
                return True  # Only download the first file

            return False
        except omero.SecurityViolation:
            # Download restricted (common on public repositories like IDR)
            return False

    def _write_file_in_chunks(self, orig_file, native_path: str):
        """Write an OMERO file to disk in chunks."""
        with open(native_path, "wb") as f:
            for chunk in orig_file.getFileInChunks():
                f.write(chunk)

    def _export_as_tiff(self, image, native_path: str):
        """Export all Z-planes and channels of the image as a multi-dimensional OME-TIFF.

        Exports all channels (C) and Z-planes at the first timepoint (T=0).
        Uses generator-based streaming to minimize memory usage - the full shape
        is declared upfront but planes are fetched and written one at a time.

        Memory usage: O(Y*X) per plane instead of O(Z*C*Y*X) for entire image.
        """
        pixels = image.getPrimaryPixels()
        size_z = image.getSizeZ()
        size_c = image.getSizeC()
        size_y = image.getSizeY()
        size_x = image.getSizeX()

        # Get dtype from first plane sample
        first_plane = pixels.getPlane(0, 0, 0)
        dtype = first_plane.dtype

        def plane_generator():
            """Generator yielding 2D planes in ZCYX order (Z outer, C inner)."""
            for z in range(size_z):
                for c in range(size_c):
                    if z == 0 and c == 0:
                        # First plane already fetched for dtype detection
                        yield first_plane
                    else:
                        yield pixels.getPlane(z, c, 0)

        with tifffile.TiffWriter(native_path, bigtiff=True, ome=True) as tif:
            tif.write(
                data=plane_generator(),
                shape=(size_z, size_c, size_y, size_x),
                dtype=dtype,
                metadata={"axes": "ZCYX"},
            )

    def _write_from(
        self, target_path: str, native_path: str, context: FilesSourceRuntimeContext[OmeroFileSourceConfiguration]
    ):
        """
        Uploading to OMERO is not supported in this implementation.
        """
        raise NotImplementedError("Uploading files to OMERO is not supported.")


__all__ = ("OmeroFileSource",)
