REMOTE_DESCRIPTION = "Use a remote driver for selenium connection."
BROWSER_DESCRIPTION = "Use specific browser for selenium (e.g. firefox or chrome)."
REMOTE_HOST_DESCRIPTION = "Selenium hub remote host to use (if remote driver in use)."
REMOTE_PORT_DESCRIPTION = "Selenium hub remote port to use (if remote driver in use)."
GALAXY_URL_DESCRIPTION = "URL of Galaxy instance to target."
HEADLESS_DESCRIPTION = "Use local selenium headlessly (native in chrome, otherwise this requires pyvirtualdisplay)."
BACKEND_DESCRIPTION = "Browser automation backend to use (selenium or playwright)."

import os
from typing import (
    Literal,
    Optional,
)
from urllib.parse import urljoin

from .driver_factory import (
    ConfiguredDriver,
    virtual_display_if_enabled,
)
from .navigates_galaxy import galaxy_timeout_handler
from .stories import (
    NoopStory,
    SectionMode,
    SectionProxy,
    Story,
    StoryProtocol,
)
from .stories.data.upload import UploadStoriesMixin


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
    parser.add_argument(
        "--timeout-multiplier",
        type=float,
        default=1.0,
        help="Multiplier to apply to all timeout values (for slower environments).",
    )
    return parser


def add_story_arguments(parser):
    """Add story generation arguments for CLI scripts.

    All the browser automation arguments (add_selenium_arguments) are also added.
    """
    add_selenium_arguments(parser)
    parser.add_argument(
        "--story-output",
        default=None,
        help="Directory to generate story documentation (markdown, HTML, PDF)",
    )
    parser.add_argument(
        "--story-title",
        default=None,
        help="Title for the generated story",
    )
    parser.add_argument(
        "--story-description",
        default=None,
        help="Description for the generated story",
    )
    parser.add_argument(
        "--only-sections",
        type=str,
        default=None,
        help='Comma-separated list of section anchors to generate (e.g., "basics,advanced")',
    )
    parser.add_argument(
        "--skip-sections",
        type=str,
        default=None,
        help="Comma-separated list of section anchors to skip",
    )
    parser.add_argument(
        "--list-sections",
        action="store_true",
        help="List all available sections and exit (requires running the script)",
    )
    parser.add_argument(
        "--merge-into",
        type=str,
        default=None,
        help="Path to existing markdown file to merge sections into",
    )
    parser.add_argument(
        "--section-mode",
        choices=["replace", "append", "standalone"],
        default="standalone",
        help="How to handle sections: replace existing, append to existing, or standalone (default)",
    )

    return parser


class DriverWrapper(UploadStoriesMixin):
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
        self.configured_driver = ConfiguredDriver(
            galaxy_timeout_handler(args.timeout_multiplier),
            browser=browser,
            remote=args.selenium_remote,
            remote_host=args.selenium_remote_host,
            remote_port=args.selenium_remote_port,
            headless=args.selenium_headless,
            backend_type=backend_type,
        )
        self.target_url = args.galaxy_url

        # Initialize story (real or noop)
        # Scripts opt-in by calling add_story_arguments()
        if hasattr(args, "story_output") and args.story_output:
            if not os.path.exists(args.story_output):
                os.makedirs(args.story_output)

            title = args.story_title or "Galaxy Tutorial"
            description = args.story_description or ""

            # Parse section filters
            only_sections = None
            skip_sections = None
            if hasattr(args, "only_sections") and args.only_sections:
                only_sections = {s.strip() for s in args.only_sections.split(",")}
            if hasattr(args, "skip_sections") and args.skip_sections:
                skip_sections = {s.strip() for s in args.skip_sections.split(",")}

            # Get section mode
            section_mode: SectionMode = getattr(args, "section_mode", "standalone")
            merge_target = getattr(args, "merge_into", None)

            self.story: StoryProtocol = Story(
                title,
                description,
                args.story_output,
                only_sections=only_sections,
                skip_sections=skip_sections,
                merge_target=merge_target,
                section_mode=section_mode,
            )
        else:
            self.story = NoopStory()

    @property
    def _driver_impl(self):
        """Provide driver implementation from configured_driver."""
        return self.configured_driver.driver_impl

    def build_url(self, url="", for_selenium: bool = True):
        return urljoin(self.target_url, url)

    def screenshot(self, label: str, caption: Optional[str] = None) -> None:
        """Save screenshot if story tracking is enabled.

        Args:
            label: Base filename for screenshot
            caption: Optional caption for the screenshot in the story
        """
        if self.story.enabled:
            # Generate screenshot path with sequential numbering
            target = os.path.join(self.story.output_directory, f"{self.story.screenshot_counter:03d}_{label}.png")
            self.story.screenshot_counter += 1

            # Save screenshot
            self.save_screenshot(target)

            # Add to story
            self.story.add_screenshot(target, caption or label)

    def section(self, title: str, anchor: str) -> SectionProxy:
        """Create a story section context manager.

        Args:
            title: Display title for the section
            anchor: Unique identifier for the section (used for filtering/merging)

        Returns:
            SectionProxy context manager
        """
        return SectionProxy(self, title, anchor)

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

    def _screenshot_path(self, label: str, extension: str = ".png") -> Optional[str]:
        return None
