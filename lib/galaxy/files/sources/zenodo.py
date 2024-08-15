from galaxy.files.sources.invenio import InvenioRDMFilesSource


class ZenodoRDMFilesSource(InvenioRDMFilesSource):
    """A files source for Zenodo repositories.

    Zenodo is an open science platform developed by CERN. It allows researchers
    to deposit data, software, and other research outputs for long-term
    preservation and sharing.

    Zenodo repositories are based on InvenioRDM, so this class is a subclass of
    InvenioRDMFilesSource with the appropriate plugin type.
    """

    plugin_type = "zenodo"

    def get_scheme(self) -> str:
        return "zenodo"


__all__ = ("ZenodoRDMFilesSource",)
