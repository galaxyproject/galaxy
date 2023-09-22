"""
GIS classes
"""
from galaxy.datatypes.binary import Binary
from galaxy.datatypes.protocols import (
    DatasetProtocol,
    HasExtraFilesAndMetadata,
)


class Shapefile(Binary):
    """The Shapefile data format:
    For more information please see http://en.wikipedia.org/wiki/Shapefile
    """

    composite_type = "auto_primary_file"
    file_ext = "shp"

    def __init__(self, **kwd):
        super().__init__(**kwd)
        self.add_composite_file("shapefile.shp", description="Geometry File (shp)", is_binary=True, optional=False)
        self.add_composite_file(
            "shapefile.shx", description="Geometry index File (shx)", is_binary=True, optional=False
        )
        self.add_composite_file(
            "shapefile.dbf", description="Columnar attributes for each shape (dbf)", is_binary=True, optional=False
        )
        # optional
        self.add_composite_file(
            "shapefile.prj", description="Projection description (prj)", is_binary=False, optional=True
        )
        self.add_composite_file(
            "shapefile.sbn", description="Spatial index of the features (sbn)", is_binary=True, optional=True
        )
        self.add_composite_file(
            "shapefile.sbx", description="Spatial index of the features (sbx)", is_binary=True, optional=True
        )
        self.add_composite_file(
            "shapefile.fbn", description="Read only spatial index of the features (fbn)", is_binary=True, optional=True
        )
        self.add_composite_file(
            "shapefile.fbx", description="Read only spatial index of the features (fbx)", is_binary=True, optional=True
        )
        self.add_composite_file(
            "shapefile.ain",
            description="Attribute index of the active fields in a table (ain)",
            is_binary=True,
            optional=True,
        )
        self.add_composite_file(
            "shapefile.aih",
            description="Attribute index of the active fields in a table (aih)",
            is_binary=True,
            optional=True,
        )
        self.add_composite_file(
            "shapefile.atx", description="Attribute index for the dbf file (atx)", is_binary=True, optional=True
        )
        self.add_composite_file("shapefile.ixs", description="Geocoding index (ixs)", is_binary=True, optional=True)
        self.add_composite_file(
            "shapefile.mxs", description="Geocoding index in ODB format (mxs)", is_binary=True, optional=True
        )
        self.add_composite_file(
            "shapefile.shp.xml", description="Geospatial metadata in XML format (xml)", is_binary=False, optional=True
        )

    def generate_primary_file(self, dataset: HasExtraFilesAndMetadata) -> str:
        rval = ["<html><head><title>Shapefile Galaxy Composite Dataset</title></head><p/>"]
        rval.append("<div>This composite dataset is composed of the following files:<p/><ul>")
        for composite_name, composite_file in self.get_composite_files(dataset=dataset).items():
            fn = composite_name
            opt_text = ""
            if composite_file.optional:
                opt_text = " (optional)"
            if composite_file.get("description"):
                rval.append(
                    f"<li><a href=\"{fn}\" type=\"application/binary\">{fn} ({composite_file.get('description')})</a>{opt_text}</li>"
                )
            else:
                rval.append(f'<li><a href="{fn}" type="application/binary">{fn}</a>{opt_text}</li>')
        rval.append("</ul></div></html>\n")
        return "\n".join(rval)

    def set_peek(self, dataset: DatasetProtocol, **kwd) -> None:
        """Set the peek and blurb text."""
        if not dataset.dataset.purged:
            dataset.peek = "Shapefile data"
            dataset.blurb = "Shapefile data"
        else:
            dataset.peek = "file does not exist"
            dataset.blurb = "file purged from disk"

    def display_peek(self, dataset: DatasetProtocol) -> str:
        """Create HTML content, used for displaying peek."""
        try:
            return dataset.peek
        except Exception:
            return "Shapefile data"
