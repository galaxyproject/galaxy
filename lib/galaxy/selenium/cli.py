REMOTE_DESCRIPTION = "Use a remote driver for selenium connection."
BROWSER_DESCRIPTION = "Use specific browser for selenium (e.g. firefox or chrome)."
REMOTE_HOST_DESCRIPTION = "Selenium hub remote host to use (if remote driver in use)."
REMOTE_PORT_DESCRIPTION = "Selenium hub remote port to use (if remote driver in use)."
GALAXY_URL_DESCRIPTION = "URL of Galaxy instance to target."
HEADLESS_DESCRIPTION = "Use local selenium headlessly (native in chrome, otherwise this requires pyvirtualdisplay)."
BACKEND_DESCRIPTION = "Browser automation backend to use (selenium or playwright)."

from typing import Literal
from urllib.parse import urljoin

from .driver_factory import (
    ConfiguredDriver,
    virtual_display_if_enabled,
)
from .navigates_galaxy import (
    galaxy_timeout_handler,
    NavigatesGalaxy,
)


def add_selenium_arguments(parser):
    """Add common selenium arguments for argparse driver utility."""

    parser.add_argument(
        "--selenium-browser",
        default="auto",
        help=BROWSER_DESCRIPTION,
    )
    parser.add_argument(
        "--selenium-headless",
        default=False,
        action="store_true",
        help=HEADLESS_DESCRIPTION,
    )
    parser.add_argument(
        "--selenium-remote",
        default=False,
        action="store_true",
        help=REMOTE_DESCRIPTION,
    )
    parser.add_argument(
        "--selenium-remote-host",
        default="127.0.0.1",
        help=REMOTE_HOST_DESCRIPTION,
    )
    parser.add_argument(
        "--selenium-remote-port",
        default="4444",
        help=REMOTE_PORT_DESCRIPTION,
    )
    parser.add_argument(
        "--galaxy_url",
        default="http://127.0.0.1:8080/",
        help=GALAXY_URL_DESCRIPTION,
    )
    parser.add_argument(
        "--backend",
        default="selenium",
        choices=["selenium", "playwright"],
        help=BACKEND_DESCRIPTION,
    )

    return parser


class DriverWrapper(NavigatesGalaxy):
    """Adapt argparse command-line options to a browser automation driver."""

    def __init__(self, args):
        browser = args.selenium_browser
        backend_type: Literal["selenium", "playwright"] = args.backend

        # Validate remote option (Playwright doesn't support remote)
        if backend_type == "playwright" and args.selenium_remote:
            raise ValueError("Playwright backend does not support remote drivers")

        # Set up virtual display for headless mode (Selenium only)
        self.display = None
        if backend_type == "selenium":
            self.display = virtual_display_if_enabled(args.selenium_headless)

        # Create configured driver with the specified backend
        # TODO: parameterize timeout multiplier
        self.configured_driver = ConfiguredDriver(
            galaxy_timeout_handler(1.0),
            browser=browser,
            remote=args.selenium_remote,
            remote_host=args.selenium_remote_host,
            remote_port=args.selenium_remote_port,
            headless=args.selenium_headless,
            backend_type=backend_type,
        )
        self.target_url = args.galaxy_url

    @property
    def _driver_impl(self):
        """Provide driver implementation from configured_driver."""
        return self.configured_driver.driver_impl

    def build_url(self, url="", for_selenium: bool = True):
        return urljoin(self.target_url, url)

    def screenshot(self, label: str) -> None:
        """No-op in this context, not saving debugging/testing screenshots.

        Consider a verbose or debug option for saving these.
        """

    @property
    def default_timeout(self):
        return 15

    def finish(self):
        """Clean up driver and display resources."""
        exception = None

        # Quit the driver (works for both backends via protocol)
        try:
            self.quit()
        except Exception as e:
            exception = e

        # Stop virtual display if used (Selenium only)
        if self.display is not None:
            try:
                self.display.stop()
            except Exception as e:
                exception = e

        if exception is not None:
            raise exception
