import os
import tempfile

import yaml
from pytest_notebook.nb_regression import NBRegressionFixture

from galaxy.util import galaxy_root_path
from ..framework import (
    SeleniumTestCase,
)


class NotebookSeleniumTestCase(SeleniumTestCase):

    def _validate_notebook(self, path):
        tempdir = tempfile.mkdtemp()
        os.symlink(os.path.join(galaxy_root_path, "lib", "galaxy"), os.path.join(tempdir, "galaxy"))
        with open(os.path.join(tempdir, "galaxy_selenium_context.yml"), "w") as f:
            context = {
                "driver": self.configured_driver.to_dict(),
                "local_galaxy_url": self.url,
                "selenium_galaxy_url": self.target_url_from_selenium,
                "timeout_multiplier": self.timeout_multiplier,
            }
            yaml.safe_dump(context, f)
        # Don't diff image outputs
        image_outputs = "/cells/*/outputs/*/data/image/png"
        diff_ignore = (image_outputs,)
        fixture = NBRegressionFixture(exec_timeout=50, exec_cwd=tempdir, diff_ignore=diff_ignore)
        fixture.diff_color_words = False
        fixture.check(path)
