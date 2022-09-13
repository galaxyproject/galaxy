/**
 * The the toolshed list of globals we expose on window.bundleToolshed.
 *
 * Everything that is exposed on this global variable is something that the python templates
 * require for their hardcoded initializations. These objects are going to have to continue
 * to exist until such time as we replace the overall application with a Vue component which
 * will handle initializations for components individually.
 */

/* jquery and _ are exposed via expose-loader while several external plugins rely on these */
import $ from "jquery";
import _ from "underscore"; // eslint-disable-line no-unused-vars

export { default as LegacyGridView } from "legacy/grid/grid-view";
export { default as ToolshedGroups } from "toolshed/toolshed.groups";
export { default as store } from "storemodern";
