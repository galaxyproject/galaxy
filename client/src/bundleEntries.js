/**
 * The list of horrible globals we expose on window.bundleEntries.
 *
 * Everything that is exposed on this global variable is something that the python templates
 * require for their hardcoded initializations. These objects are going to have to continue
 * to exist until such time as we replace the overall application with a Vue component which
 * will handle initializations for components individually.
 *
 */
import { replaceChildrenWithComponent } from "utils/mountVueComponent";

import TabularChunkedView from "components/Visualizations/Tabular/TabularChunkedView.vue";

// webapps/galaxy/dataset/{ display | tabular_chunked }.mako
export const createTabularDatasetChunkedView = (options) => {
    return replaceChildrenWithComponent(options.parent_elt, TabularChunkedView, { options });
};
