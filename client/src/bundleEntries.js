/**
 * The big list of horrible globals we expose on window.bundleEntries.
 *
 * Everything that is exposed on this global variable is something that the python templates
 * require for their hardcoded initializations. These objects are going to have to continue
 * to exist until such time as we replace the overall application with a Vue component which
 * will handle initializations for components individually.
 */

/* jquery and _ are exposed via expose-loader while several external plugins rely on these */
import $ from "jquery"; // eslint-disable-line no-unused-vars
import Client from "mvc/visualization/chart/chart-client";
import _ from "underscore"; // eslint-disable-line no-unused-vars
import { TracksterUIView } from "viz/trackster";

// Previously "chart"

export { getGalaxyInstance, setGalaxyInstance } from "app";
export { runTour } from "components/Tour/runTour";
export { default as LegacyGridView } from "legacy/grid/grid-view";
export { createTabularDatasetChunkedView } from "mvc/dataset/data";
export { create_chart, create_histogram } from "reports/run_stats";
export { Toast } from "ui/toast"; // TODO: remove when external consumers are updated/gone (IES right now)
export { TracksterUI } from "viz/trackster";

export function trackster(options) {
    new TracksterUIView(options);
}

// Previously wandering around as window.thing = thing in the onload script
export { hide_modal, Modal, show_in_overlay, show_message, show_modal } from "layout/modal";
export { make_popup_menus, make_popupmenu } from "ui/popupmenu";
export { default as async_save_text } from "utils/async-save-text";
export function chart(options) {
    return new Client(options);
}

// Used in common.mako
export { default as store } from "storemodern";
