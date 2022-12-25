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
import _ from "underscore"; // eslint-disable-line no-unused-vars

export { getGalaxyInstance, setGalaxyInstance } from "app";
import { TracksterUIView } from "viz/trackster";
export { TracksterUI } from "viz/trackster";
import Circster from "viz/circster";
export { PhylovizView as phyloviz } from "viz/phyloviz";
export { SweepsterVisualization, SweepsterVisualizationView } from "viz/sweepster";
export { createTabularDatasetChunkedView } from "mvc/dataset/data";
export { default as LegacyGridView } from "legacy/grid/grid-view";
export { create_chart, create_histogram } from "reports/run_stats";
export { runTour } from "components/Tour/runTour";
export { Toast } from "ui/toast"; // TODO: remove when external consumers are updated/gone (IES right now)

export function trackster(options) {
    new TracksterUIView(options);
}

export function circster(options) {
    new Circster.GalaxyApp(options);
}

// Previously wandering around as window.thing = thing in the onload script
export { show_in_overlay, hide_modal, show_message, show_modal, Modal } from "layout/modal";
export { make_popupmenu, make_popup_menus } from "ui/popupmenu";
export { default as async_save_text } from "utils/async-save-text";

// Previously "chart"
import Client from "mvc/visualization/chart/chart-client";
export function chart(options) {
    return new Client(options);
}

export { mountMakoTags } from "components/Tags";

// Used in common.mako
export { default as store } from "storemodern";
