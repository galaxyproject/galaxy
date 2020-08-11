import $ from "jquery";

// If galaxy_main frame does not exist and link targets galaxy_main,
// add use_panels=True and set target to self.
export function adjustIframeLinks() {
    console.log("adjustIframeLinks");

    $("a").click(function () {
        var anchor = $(this);
        var galaxy_main_exists = window.parent.frames && window.parent.frames.galaxy_main;
        if (anchor.attr("target") == "galaxy_main" && !galaxy_main_exists) {
            var href = anchor.attr("href");
            if (href.indexOf("?") == -1) {
                href += "?";
            } else {
                href += "&";
            }
            href += "use_panels=True";
            anchor.attr("href", href);
            anchor.attr("target", "_self");
        }
        return anchor;
    });
}

/**
 * Adds an identifying class at the document root so that we can tell when we're
 * inside an iframe from inside the css, removing the need for all those
 * pointless conditional checks to apply iframe-only styles.
 */
export function addIframeClass() {
    console.log("addIframeClass");
    if (window.self !== window.top) {
        console.log(">>> We are in an iframe");
        document.body.classList.add("framed");
    }
}
