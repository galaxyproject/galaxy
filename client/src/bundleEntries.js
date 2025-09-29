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
 * tagging_common.mako: show_in_overlay
 */

/* jquery and _ are exposed via expose-loader while several external plugins rely on these */
import $ from "jquery"; // eslint-disable-line no-unused-vars
import _ from "underscore"; // eslint-disable-line no-unused-vars

export { getGalaxyInstance, setGalaxyInstance } from "app";
export { default as LegacyGridView } from "legacy/grid/grid-view";
export { createTabularDatasetChunkedView } from "mvc/dataset/data";
export { create_chart, create_histogram } from "reports/run_stats";
export { Toast } from "ui/toast"; // TODO: remove when external consumers are updated/gone (IES right now)

// Previously wandering around as window.thing = thing in the onload script
export { show_in_overlay } from "layout/modal";

// Used in common.mako
export { default as store } from "storemodern";
