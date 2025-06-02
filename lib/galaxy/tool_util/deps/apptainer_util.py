import logging
import os
import platform
import tempfile
from typing import (
    List,
    Optional,
    Union,
)

import packaging.version

from galaxy.util import (
    commands,
    download_to_file,
)
from . import installable

DEFAULT_APPTAINER_COMMAND = "apptainer"
APPTAINER_VERSION = "1.4.0"
APPTAINER_URL_TEMPLATE = "https://github.com/galaxyproject/apptainer-build-unprivileged/releases/download/v{version}/apptainer-{version}-{el}-{arch}.tar.gz"


log = logging.getLogger(__name__)


def _glibc_version() -> Optional[packaging.version.Version]:
    try:
        # First line should always be 'ldd (dist-specific) VERSION'
        glibc_version = commands.execute(["ldd", "--version"]).splitlines()[0].split()[-1]
        return packaging.version.parse(glibc_version)
    except Exception as exc:
        log.warning(f"Unable to get glibc version: {str(exc)}")


def apptainer_url() -> str:
    glibc_version = _glibc_version()
    el = "el8"
    if glibc_version >= packaging.version.parse("2.34"):
        el = "el9"
    url = APPTAINER_URL_TEMPLATE.format(version=APPTAINER_VERSION, el=el, arch=platform.machine())
    return url


class ApptainerContext(installable.InstallableContext):
    installable_description = "Apptainer"

    def __init__(
        self,
        apptainer_prefix: Optional[str] = None,
        apptainer_exec: Optional[Union[str, List[str]]] = None,
    ) -> None:
        self.apptainer_prefix = apptainer_prefix

        if apptainer_exec and isinstance(apptainer_exec, str):
            apptainer_exec = os.path.normpath(apptainer_exec)

        if apptainer_exec is not None:
            self.apptainer_exec = apptainer_exec
        elif apptainer_prefix is not None:
            self.apptainer_exec = os.path.join(apptainer_prefix, "bin", "apptainer")
        else:
            self.apptainer_exec = "apptainer"

    def apptainer_version(self) -> str:
        cmd = [self.apptainer_exec, "version"]
        version_out = commands.execute(cmd).strip()
        return version_out

    def is_installed(self) -> bool:
        try:
            self.apptainer_version()
            return True
        except Exception:
            return False

    def can_install(self) -> bool:
        if self.apptainer_prefix is None:
            return False
        if platform.system() != "Linux" or platform.machine() not in ("x86_64", "aarch64"):
            return False
        glibc_version = _glibc_version()
        if not glibc_version or glibc_version < packaging.version.parse("2.28"):
            return False
        return True

    @property
    def parent_path(self) -> Optional[str]:
        if self.apptainer_prefix:
            return os.path.dirname(os.path.abspath(self.apptainer_prefix))


def install_apptainer(apptainer_context: ApptainerContext) -> int:
    with tempfile.NamedTemporaryFile(suffix=".tar.gz", prefix="apptainer_install", delete=False) as temp:
        tarball_path = temp.name
    install_cmd = ["tar", "zxf", tarball_path, "-C", apptainer_context.apptainer_prefix, "--strip-components=1"]
    fetch_url = apptainer_url()
    log.info("Installing Apptainer, this may take several minutes.")
    log.info(f"Fetching from: {fetch_url}")
    try:
        os.makedirs(apptainer_context.apptainer_prefix)
        download_to_file(fetch_url, tarball_path)
        commands.execute(install_cmd)
    except Exception:
        log.exception("Failed to fetch Apptainer tarball")
        return 1
    finally:
        if os.path.exists(tarball_path):
            os.remove(tarball_path)
    log.info(f"Apptainer installed to: {apptainer_context.apptainer_prefix}")
