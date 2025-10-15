/**
 * The list of horrible globals we expose on window.bundleEntries.
 *
 * Everything that is exposed on this global variable is something that the python templates
 * require for their hardcoded initializations. These objects are going to have to continue
 * to exist until such time as we replace the overall application with a Vue component which
 * will handle initializations for components individually.
 *
 * legacy/grid_base.mako: window.bundleEntries.LegacyGridView
 * webapps/galaxy/dataset/tabular_chunked.mako: window.bundleEntries.createTabularDatasetChunkedView
 * webapps/galaxy/dataset/display.mako: window.bundleEntries.createTabularDatasetChunkedView
 * webapps/reports/run_stats.mako: window.bundleEntries.create_chart
 * webapps/reports/run_stats.mako: window.bundleEntries.create_histogram
 */

import _ from "underscore";
import { replaceChildrenWithComponent } from "utils/mountVueComponent";
import TabularChunkedView from "components/Visualizations/Tabular/TabularChunkedView.vue";

export { getGalaxyInstance, setGalaxyInstance } from "app";
export { default as LegacyGridView } from "legacy/grid/grid-view";
export { create_chart, create_histogram } from "reports/run_stats";

export const createTabularDatasetChunkedView = (options) => {
    return replaceChildrenWithComponent(options.parent_elt, TabularChunkedView, { options });
};

// Used in common.mako
export { default as store } from "storemodern";
