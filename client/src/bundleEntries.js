/**
 * The list of globals we expose on window.bundleEntries.
 */

// legacy/grid_base.mako
export { default as LegacyGridView } from "@/legacy/grid/grid-view";

// webapps/reports/run_stats.mako
export { create_chart, create_histogram } from "@/reports/run_stats";
