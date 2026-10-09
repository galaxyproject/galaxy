"""Helpers for dynamic job destination rules that route jobs by conda platform.

A destination declares the conda platform (subdir) of its nodes with the
``platform`` destination parameter, for example ``platform: linux-aarch64``.
:func:`platform_destination` picks the first destination whose platform has
conda environments for all requirements of the tool.
"""

from typing import (
    Any,
    Optional,
    Union,
)

from galaxy.jobs.mapper import JobMappingException


def platform_destination(
    app: Any,
    tool: Any,
    job: Any,
    destinations: Union[dict[str, str], list[str]],
    default: Optional[str] = None,
) -> str:
    """Return the id of the first destination whose platform can run ``tool``.

    ``destinations`` is either a mapping of destination id to platform, or a
    list of destination ids whose ``platform`` parameter is read from the job
    configuration. The order of ``destinations`` is the order of preference.
    A tool without package requirements gets the first destination.

    If no destination matches, ``default`` is returned, or a
    :class:`JobMappingException` is raised when ``default`` is ``None``.
    """
    if not destinations:
        raise JobMappingException("No destinations given for platform routing.")
    if isinstance(destinations, dict):
        platform_of = dict(destinations)
    else:
        platform_of = {id_: _configured_platform(app, id_) for id_ in destinations}

    requirements = getattr(tool, "requirements", None)
    packages = list(requirements.packages) if requirements else []
    if not packages:
        return next(iter(platform_of))

    available = app.toolbox.dependency_manager.platforms_for_requirements(requirements.packages)
    for destination_id, platform in platform_of.items():
        if platform in available:
            return destination_id
    if default is not None:
        return default
    raise JobMappingException(
        f"No job destination can run tool '{getattr(tool, 'id', None)}' (job {getattr(job, 'id', None)}): its "
        f"requirements are installed for platforms [{', '.join(available) or 'none'}], the destinations offer "
        f"[{', '.join(sorted({p for p in platform_of.values() if p}))}]."
    )


def _configured_platform(app: Any, destination_id: str) -> Optional[str]:
    return app.job_config.get_destination(destination_id).params.get("platform")
