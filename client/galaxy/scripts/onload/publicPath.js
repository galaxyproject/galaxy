/**
 * Set dynamically loaded webpack public path. (https://webpack.js.org/guides/public-path/#on-the-fly)
 * This is, by default, just `/static/dist/`, but if galaxy is being served at
 * a prefix (e.g.  `<server>/galaxy/`), this must be accounted for before any
 * dynamic bundle imports load, otherwise they will fail.
 */

/* global __webpack_public_path__:writable */

import { getRootFromIndexLink } from "./getRootFromIndexLink";

__webpack_public_path__ = `${getRootFromIndexLink().replace(/\/+$/, "")}/static/scripts/bundled/`;
