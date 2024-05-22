import "@citation-js/plugin-bibtex";
import "@citation-js/plugin-csl";

import { plugins } from "@citation-js/core";

export { Cite } from "@citation-js/core";

plugins.config.get("@bibtex");
plugins.config.get("@csl");
