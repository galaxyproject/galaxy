from tempfile import NamedTemporaryFile
from typing import Optional

import click
import yaml

from galaxy.app import GalaxyManagerApplication
from galaxy.managers.tool_data import ToolDataImportManager


@click.command(help="Import tool data bundle. URI can be a path to a zipped file or directory.")
@click.option("-c", "--galaxy-config-file", type=click.Path(exists=True, resolve_path=True))
@click.option(
    "-t",
    "--tool-data-file-path",
    type=click.Path(exists=True, resolve_path=True),
    help="loc file to append data to. Must be be loaded in general data tables",
)
@click.argument("uri")
def run_import_data_bundle(uri: str, galaxy_config_file: str, tool_data_file_path: Optional[str] = None):

    with open(galaxy_config_file) as fh:
        galaxy_config = yaml.safe_load(fh)
        galaxy_config["file_sources"] = []
        galaxy_config["file_source_config_file"] = None
        galaxy_config["vault_config_file"] = NamedTemporaryFile().name
    app = GalaxyManagerApplication(
        use_converters=False,
        use_display_applications=False,
        configure_logging=False,
        check_migrate_databases=False,
        **galaxy_config,
    )
    import_manager = ToolDataImportManager(app)
    import_manager.import_data_bundle_by_uri(app.config, uri=uri, tool_data_file_path=tool_data_file_path)


if __name__ == "__main__":
    run_import_data_bundle()
