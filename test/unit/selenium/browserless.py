"""A selenium context that never launches a browser."""

from galaxy.selenium.context import GalaxySeleniumContextImpl


class BrowserlessContext(GalaxySeleniumContextImpl):
    def __init__(self):
        # Skip building a ConfiguredDriver, which would launch a browser.
        pass

    def save_screenshot(self, path: str) -> None:
        with open(path, "wb") as f:
            f.write(b"screenshot")
