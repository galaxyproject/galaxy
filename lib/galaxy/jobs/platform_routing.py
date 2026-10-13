"""Helpers for dynamic job destination rules that route jobs by conda platform.

A destination declares the conda platform (subdir) of its nodes with the
``platform`` destination parameter, for example ``platform: linux-aarch64``.
:func:`platform_destination` picks the first destination whose platform has
conda environments for all requirements of the tool.
"""

from typing import (
    Any,
)

from galaxy.jobs.mapper import JobMappingException


def platform_destination(
    app: Any,
    tool: Any,
    job: Any,
    destinations: dict[str, str] | list[str],
    default: str | None = None,
) -> str:
    """Return the id of the first destination whose platform can run ``tool``.

    ``destinations`` is either a mapping of destination id to platform, or a
    list of destination ids whose ``platform`` parameter is read from the job
    configuration. The order of ``destinations`` is the order of preference.
    A tool without package requirements gets the first destination.
    If nothing is installed for the tool on any platform and the conda resolver has auto_install enabled, the first
    destination with the native platform is returned, so that the job-time install creates the environments.
    When that platform has a recent failed install of the tool (a package that does not exist for it), the first
    destination of another configured platform without such a failure is returned instead.
    Every listed destination needs a ``platform`` parameter (or an entry in the mapping).

    If no destination matches, ``default`` is returned, or a
    :class:`JobMappingException` is raised when ``default`` is ``None``.
    """
    if not destinations:
        raise JobMappingException("No destinations given for platform routing.")
    platform_of: dict[str, str | None]
    if isinstance(destinations, dict):
        platform_of = dict(destinations)
    else:
        platform_of = {id_: _configured_platform(app, id_) for id_ in destinations}
    for destination_id, platform in platform_of.items():
        if not platform:
            raise JobMappingException(
                f"Job destination '{destination_id}' is used for platform routing but has no 'platform' parameter, "
                "set it in the job configuration (for example platform: linux-aarch64)."
            )

    requirements = getattr(tool, "requirements", None)
    packages = list(requirements.packages) if requirements else []
    if requirements is None or not packages:
        return next(iter(platform_of))

    dependency_manager = app.toolbox.dependency_manager
    available = dependency_manager.platforms_for_requirements(requirements.packages)
    for destination_id, platform in platform_of.items():
        if platform in available:
            return destination_id
    configured = dependency_manager.configured_conda_platforms()
    if not available and configured and dependency_manager.conda_auto_install_enabled():
        # Nothing is installed anywhere yet. The job-time auto-install on a native destination creates the
        # environments for all platforms, so later jobs of the tool route normally.
        failed = dependency_manager.platforms_with_failed_install(requirements.packages)
        allowed = [p for p in configured if p not in failed] if configured[0] in failed else configured[:1]
        for destination_id, platform in platform_of.items():
            if platform in allowed:
                return destination_id
    if default is not None:
        return default
    if not configured:
        raise JobMappingException(
            f"No job destination can run tool '{getattr(tool, 'id', None)}' (job {getattr(job, 'id', None)}): no "
            "conda platforms are configured, set conda_platforms (or the platforms option of the conda dependency "
            "resolver) so that conda environments are maintained for the platforms of the destinations "
            f"[{', '.join(sorted({p for p in platform_of.values() if p}))}]."
        )
    raise JobMappingException(
        f"No job destination can run tool '{getattr(tool, 'id', None)}' (job {getattr(job, 'id', None)}): its "
        f"requirements are installed for platforms [{', '.join(available) or 'none'}], the destinations offer "
        f"[{', '.join(sorted({p for p in platform_of.values() if p}))}]. The environments must be installed first, "
        "for example with the admin dependency API or UI, or by enabling auto_install of the conda resolver."
    )


def _configured_platform(app: Any, destination_id: str) -> str | None:
    platform: str | None = app.job_config.get_destination(destination_id).params.get("platform")
    return platform
