from contextlib import contextmanager
from datetime import datetime
from typing import (
    Iterator,
    Optional,
    Union,
)

from omero.gateway import BlitzGateway

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

    template_config_class = OmeroFileSourceTemplateConfiguration
    resolved_config_class = OmeroFileSourceConfiguration

    def __init__(self, template_config: OmeroFileSourceTemplateConfiguration):
        super().__init__(template_config)

    @contextmanager
    def _connection(self, context: FilesSourceRuntimeContext[OmeroFileSourceConfiguration]) -> Iterator[BlitzGateway]:
        """Context manager for OMERO connections with automatic cleanup.

        Establishes a connection to the OMERO server, enables keepalive for long-running
        operations, and ensures proper cleanup on exit.
        """
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
            conn.c.enableKeepAlive(60)  # type: ignore[union-attr]
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
            results = self._list_entries_for_path(omero, path_parts)
            return results, len(results)

    def _parse_path(self, path: str) -> list[str]:
        """Parse and normalize the path into components."""
        return [p for p in path.strip("/").split("/") if p]

    def _list_entries_for_path(self, omero: BlitzGateway, path_parts: list[str]) -> list[AnyRemoteEntry]:
        """List entries based on the path depth."""
        if len(path_parts) == 0:
            return self._list_projects(omero)
        elif len(path_parts) == 1:
            return self._list_datasets(omero, path_parts[0])
        elif len(path_parts) == 2:
            return self._list_images(omero, path_parts[0], path_parts[1])
        return []

    def _list_projects(self, omero: BlitzGateway) -> list[AnyRemoteEntry]:
        """List all projects as directories at root level."""
        results: list[AnyRemoteEntry] = []
        for project in omero.getObjects("Project"):
            project_path = f"project_{project.getId()}"
            results.append(
                RemoteDirectory(
                    name=project.getName() or f"Project {project.getId()}",
                    uri=self.uri_from_path(project_path),
                    path=project_path,
                )
            )
        return results

    def _list_datasets(self, omero: BlitzGateway, project_id_str: str) -> list[AnyRemoteEntry]:
        """List datasets within a project."""
        if not project_id_str.startswith("project_"):
            return []

        project_id = self._extract_id(project_id_str, "project_")
        project = omero.getObject("Project", project_id)
        if not project:
            return []

        results: list[AnyRemoteEntry] = []
        for dataset in project.listChildren():
            dataset_path = f"{project_id_str}/dataset_{dataset.getId()}"
            results.append(
                RemoteDirectory(
                    name=dataset.getName() or f"Dataset {dataset.getId()}",
                    uri=self.uri_from_path(dataset_path),
                    path=dataset_path,
                )
            )
        return results

    def _list_images(self, omero: BlitzGateway, project_id_str: str, dataset_id_str: str) -> list[AnyRemoteEntry]:
        """List images within a dataset."""
        if not dataset_id_str.startswith("dataset_"):
            return []

        dataset_id = self._extract_id(dataset_id_str, "dataset_")
        dataset = omero.getObject("Dataset", dataset_id)
        if not dataset:
            return []

        results: list[AnyRemoteEntry] = []
        for image in dataset.listChildren():
            image_path = f"{project_id_str}/{dataset_id_str}/image_{image.getId()}"
            results.append(self._create_remote_file_for_image(image, image_path))
        return results

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

        self._export_pixel_data(image, native_path)

    def _try_download_original_file(self, image, native_path: str) -> bool:
        """Attempt to download the original imported file. Returns True if successful."""
        if image.countFilesetFiles() == 0:
            return False

        for orig_file in image.getImportedImageFiles():
            self._write_file_in_chunks(orig_file, native_path)
            return True  # Only download the first file

        return False

    def _write_file_in_chunks(self, orig_file, native_path: str):
        """Write an OMERO file to disk in chunks."""
        with open(native_path, "wb") as f:
            for chunk in orig_file.getFileInChunks():
                f.write(chunk)

    def _export_pixel_data(self, image, native_path: str):
        """Export pixel data as TIFF or fallback to thumbnail."""
        try:
            self._export_as_tiff(image, native_path)
        except Exception:
            self._export_as_thumbnail(image, native_path)

    def _export_as_tiff(self, image, native_path: str):
        """Export all Z-planes of the image as a multi-page TIFF.

        Exports the first channel (C=0) and first timepoint (T=0) across all Z-planes.
        This preserves the full Z-stack for 3D analysis while keeping the export manageable.
        """
        from PIL import Image as PILImage

        pixels = image.getPrimaryPixels()
        size_z = image.getSizeZ()

        planes = []
        for z in range(size_z):
            plane_data = pixels.getPlane(z, 0, 0)
            planes.append(PILImage.fromarray(plane_data))

        if planes:
            planes[0].save(
                native_path,
                format="TIFF",
                save_all=True,
                append_images=planes[1:] if len(planes) > 1 else [],
            )

    def _export_as_thumbnail(self, image, native_path: str):
        """Export the rendered thumbnail as final fallback."""
        img_data = image.getThumbnail()
        with open(native_path, "wb") as f:
            f.write(img_data)

    def _write_from(
        self, target_path: str, native_path: str, context: FilesSourceRuntimeContext[OmeroFileSourceConfiguration]
    ):
        """
        Uploading to OMERO is not supported in this implementation.
        """
        raise NotImplementedError("Uploading files to OMERO is not supported.")


__all__ = ("OmeroFileSource",)
