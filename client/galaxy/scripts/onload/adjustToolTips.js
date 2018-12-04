/**
 * TODO: Put this with the appropriate UI code
 */

import $ from "jquery";

// Put tooltips below items in panel header so that they do not overlap masthead.
export function adjustToolTips() {
    console.log("adjustToolTips");

    if ($.fn.tooltip) {
        $(".unified-panel-header [title]").tooltip({ placement: "bottom" });
        // default tooltip initialization, it will follow the data-placement tag for tooltip location
        // and fallback to 'top' if not present
        $("[title]").tooltip();
    }
}