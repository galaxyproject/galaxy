// Initialize refresh events.
import $ from "jquery";

export function initTooltips() {
    console.log("initTooltips");

    // Tooltips
    if ($.fn.tooltip) {
        // Put tooltips below items in panel header so that they do not overlap masthead.
        $(".unified-panel-header [title]").tooltip({ placement: "bottom" });

        // default tooltip initialization, it will follow the data-placement tag for tooltip location
        // and fallback to 'top' if not present
        $("[title]").tooltip();
    }
}
