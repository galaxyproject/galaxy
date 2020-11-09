import json
import logging

from pkg_resources import resource_string

log = logging.getLogger(__name__)

# https://docs.google.com/document/d/16vnRtDjrx5eHSl4jXs2vMaDTI6luyyLzU6xMvRHsnbI/edit#heading=h.1pihjj16olz2
RECOMMENDED_LICENSES = [
    "Apache-2.0",
    "Artistic-2.0",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "CC-BY-4.0",
    "CC-BY-SA-4.0",
    "CC0-1.0",
    "EPL-2.0",
    "AGPL-3.0-or-later",
    "GPL-3.0-or-later",
    "MIT",
    "MPL-2.0",
    "PDDL-1.0",
]
SPDX_LICENSES_STRING = resource_string(__name__, 'licenses.json').decode("UTF-8")
SPDX_LICENSES = json.loads(SPDX_LICENSES_STRING)
for license in SPDX_LICENSES["licenses"]:
    license["recommended"] = license["licenseId"] in RECOMMENDED_LICENSES
    license["spdxUrl"] = "https://spdx.org/licenses/%s" % license["reference"][len("./"):]
    seeAlso = license.get("seeAlso", [])
    if len(seeAlso) > 0:
        url = seeAlso[0]
    else:
        url = license["spdxUrl"]
    license["url"] = url


class LicensesManager:

    def __init__(self):
        by_index = {}
        for spdx_license in self.index():

            by_index[spdx_license["licenseId"]] = spdx_license
            by_index[spdx_license["detailsUrl"]] = spdx_license
            for seeAlso in spdx_license.get("seeAlso", []):
                by_index[seeAlso] = spdx_license
        self._by_index = by_index

    def index(self):
        return SPDX_LICENSES["licenses"]

    def get(self, uri):
        if uri in self._by_index:
            return self._by_index[uri]
        else:
            log.warn("Unknown license URI encountered [%s]" % uri)
        return {
            "url": uri
        }
