"""
API operations allowing clients to determine datatype supported by Galaxy.
"""

import logging
from typing import (
    cast,
    Dict,
    List,
    Optional,
    Union,
)

from fastapi import (
    Path,
    Query,
    Response,
)

from galaxy.datatypes.registry import Registry
from galaxy.managers.datatypes import (
    DatatypeConverterList,
    DatatypeDetails,
    DatatypesCombinedMap,
    DatatypesEDAMDetailsDict,
    DatatypesMap,
    DatatypeVisualizationMappingsList,
    view_converters,
    view_edam_data,
    view_edam_formats,
    view_index,
    view_mapping,
    view_sniffers,
    view_visualization_mappings,
)
from . import (
    depends,
    Router,
)

log = logging.getLogger(__name__)

router = Router(tags=["datatypes"])

ExtensionOnlyQueryParam: Optional[bool] = Query(
    default=True,
    title="Extension only",
    description="Whether to return only the datatype's extension rather than the datatype's details",
)

UploadOnlyQueryParam: Optional[bool] = Query(
    default=True,
    title="Upload only",
    description="Whether to return only datatypes which can be uploaded",
)

IdentifierOnly: Optional[bool] = Query(
    default=True,
    title="prefixIRI only",
    description="Whether to return only the EDAM prefixIRI rather than the EDAM details",
)


@router.cbv
class FastAPIDatatypes:
    datatypes_registry: Registry = depends(Registry)

    @router.get(
        "/api/datatypes",
        public=True,
        summary="Lists all available data types",
        response_description="List of data types",
    )
    async def index(
        self,
        extension_only: Optional[bool] = ExtensionOnlyQueryParam,
        upload_only: Optional[bool] = UploadOnlyQueryParam,
    ) -> Union[List[DatatypeDetails], List[str]]:
        """Gets the list of all available data types."""
        return view_index(self.datatypes_registry, extension_only, upload_only)

    @router.get(
        "/api/datatypes/{datatype}",
        public=True,
        summary="Get details for a specific datatype",
        response_description="Detailed information about a datatype",
    )
    async def show(
        self,
        datatype: str = Path(
            ...,
            title="Datatype",
            description="Datatype extension to get information for",
            examples=["bam", "h5", "vcf"],
        ),
    ):
        """Gets detailed information about a specific datatype.

        Includes information about:
        - Basic properties (description, mime type, etc.)
        - Available converters
        - EDAM mappings
        - Preferred visualization
        """
        # Get the datatype object
        dt_object = self.datatypes_registry.get_datatype_by_extension(datatype)
        if dt_object is None:
            return Response(status_code=404, content=f"Datatype '{datatype}' not found")

        # Basic information
        result = {
            "extension": datatype,
            "description": getattr(dt_object, "description", None),
            "display_in_upload": datatype in self.datatypes_registry.upload_file_formats,
            "mimetype": self.datatypes_registry.get_mimetype_by_extension(datatype),
            "is_binary": getattr(dt_object, "is_binary", False),
        }

        # Add composite files if applicable
        composite_files = getattr(dt_object, "composite_files", None)
        if composite_files:
            result["composite_files"] = [{"name": k, **v.dict()} for k, v in composite_files.items()]

        # Add EDAM information if available
        edam_format = self.datatypes_registry.edam_formats.get(datatype)
        if edam_format:
            result["edam_format"] = edam_format

        edam_data = self.datatypes_registry.edam_data.get(datatype)
        if edam_data:
            result["edam_data"] = edam_data

        # Add converter information
        converters = self.datatypes_registry.get_converters_by_datatype(datatype)
        if converters:
            result["converters"] = list(converters.keys())

        # Add preferred visualization if any
        preferred_viz = self.datatypes_registry.get_preferred_visualization(datatype)
        if preferred_viz:
            result["preferred_visualization"] = {
                "visualization": preferred_viz["visualization"],
            }

        return result

    @router.get(
        "/api/datatypes/mapping",
        public=True,
        summary="Returns mappings for data types and their implementing classes",
        response_description="Dictionary to map data types with their classes",
    )
    async def mapping(self) -> DatatypesMap:
        """Gets mappings for data types."""
        return view_mapping(self.datatypes_registry)

    @router.get(
        "/api/datatypes/types_and_mapping",
        public=True,
        summary="Returns all the data types extensions and their mappings",
        response_description="Dictionary to map data types with their classes",
    )
    async def types_and_mapping(
        self,
        extension_only: Optional[bool] = ExtensionOnlyQueryParam,
        upload_only: Optional[bool] = UploadOnlyQueryParam,
    ) -> DatatypesCombinedMap:
        """Combines the datatype information from (/api/datatypes) and the
        mapping information from (/api/datatypes/mapping) into a single
        response."""
        return DatatypesCombinedMap(
            datatypes=view_index(self.datatypes_registry, extension_only, upload_only),
            datatypes_mapping=view_mapping(self.datatypes_registry),
        )

    @router.get(
        "/api/datatypes/sniffers",
        public=True,
        summary="Returns the list of all installed sniffers",
        response_description="List of datatype sniffers",
    )
    async def sniffers(self) -> List[str]:
        """Gets the list of all installed data type sniffers."""
        return view_sniffers(self.datatypes_registry)

    @router.get(
        "/api/datatypes/converters",
        public=True,
        summary="Returns the list of all installed converters",
        response_description="List of all datatype converters",
    )
    async def converters(self) -> DatatypeConverterList:
        """Gets the list of all installed converters."""
        return view_converters(self.datatypes_registry)

    @router.get(
        "/api/datatypes/edam_formats",
        public=True,
        summary="Returns a dictionary/map of datatypes and EDAM formats",
        response_description="Dictionary/map of datatypes and EDAM formats",
    )
    async def edam_formats(self) -> Dict[str, str]:
        """Gets a map of datatypes and their corresponding EDAM formats."""
        return cast(Dict[str, str], view_edam_formats(self.datatypes_registry))

    @router.get(
        "/api/datatypes/edam_formats/detailed",
        public=True,
        summary="Returns a dictionary of datatypes and EDAM format details",
        response_description="Dictionary of EDAM format details containing the EDAM iri, label, and definition",
        response_model=DatatypesEDAMDetailsDict,
    )
    async def edam_formats_detailed(self):
        """Gets a map of datatypes and their corresponding EDAM formats.
        EDAM formats contain the EDAM iri, label, and definition."""
        return view_edam_formats(self.datatypes_registry, True)

    @router.get(
        "/api/datatypes/edam_data",
        public=True,
        summary="Returns a dictionary/map of datatypes and EDAM data",
        response_description="Dictionary/map of datatypes and EDAM data",
    )
    async def edam_data(self) -> Dict[str, str]:
        """Gets a map of datatypes and their corresponding EDAM data."""
        return cast(Dict[str, str], view_edam_data(self.datatypes_registry))

    @router.get(
        "/api/datatypes/edam_data/detailed",
        public=True,
        summary="Returns a dictionary of datatypes and EDAM data details",
        response_description="Dictionary of EDAM data details containing the EDAM iri, label, and definition",
        response_model=DatatypesEDAMDetailsDict,
    )
    async def edam_data_detailed(self):
        """Gets a map of datatypes and their corresponding EDAM data.
        EDAM data contains the EDAM iri, label, and definition."""
        return view_edam_data(self.datatypes_registry, True)

    @router.get(
        "/api/datatypes/{datatype}/visualizations",
        public=True,
        summary="Returns the visualization mapping for a specific datatype",
        response_description="Visualization mapping for the specified datatype",
        response_model=DatatypeVisualizationMappingsList,
    )
    async def visualization_for_datatype(
        self,
        datatype: str = Path(
            ...,
            title="Datatype",
            description="Datatype extension to get visualization mapping for",
            examples=["bam", "h5"],
        ),
    ) -> DatatypeVisualizationMappingsList:
        """Gets the visualization mapping for a specific datatype.

        Mappings are defined in the datatypes_conf.xml configuration file.
        """
        return view_visualization_mappings(self.datatypes_registry, datatype)
