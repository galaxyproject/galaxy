import { plugins } from "@citation-js/core";
export { Cite } from "@citation-js/core";
import "@citation-js/plugin-bibtex";
import "@citation-js/plugin-csl";

plugins.config.get("@bibtex");
plugins.config.get("@csl");
