$(document).ready(function () {
    var gtnWebhookLoaded = false;

    function showOverlay() {
        $(".gtn-screen-overlay").show();
        $(".gtn-screen").show();
    }

    function removeOverlay() {
        $(".gtn-screen-overlay").hide();
        $(".gtn-screen").hide();
    }

    function addIframe() {
        gtnWebhookLoaded = true;
        var url, message;

        // Test for the presence of /training-material/. If that is available we
        // can opt in the fancy click-to-run features. Otherwise we fallback to
        // displaying the real GTN.
        var jqxhr = $.get("/training-material/", function () {
            url = "/training-material/";
            message = "";
        }).fail(function () {
            url = "https://training.galaxyproject.org/training-material/";
            message =
                '<span><a href="https://docs.galaxyproject.org/en/master/admin/special_topics/gtn.html">Click to run</a> unavailable.</span>';
        });

        parentElement.prepend(`
			<div id="gtn_screen_overlay" class="gtn-screen-overlay"></div>
			<div id="gtn_screen" class="gtn-screen">
				<div class="gtn-header">
					<iframe id="gtn-embed" src="${url}" width="80%" height="80%"></iframe>
					${message}
				</div>
			</div>
	   `);

        // Clicking outside of GTN closes it
        $("#gtn_screen").click(function () {
            self.removeOverlay();
        });

        // Depends on the iframe being present
        $("#gtn-embed").on("load", function () {
            //new_url = document.getElementById("gtn-embed").contentWindow.location.href;
            var gtn_tools = $("#gtn-embed").contents().find("span[data-tool]");
            // Buttonify
            gtn_tools.addClass("btn btn-primary");

            gtn_tools.click(function (e) {
                var target = e.target;

                // Sometimes we get the i or the strong, not the parent.
                if (e.target.tagName.toLowerCase() !== "span") {
                    target = e.target.parentElement;
                }

                tool_id = $(target).data("tool");
                tool_version = $(target).data("version");

                if (tool_id === "upload1" || tool_id === "upload") {
                    Galaxy.upload.show();
                } else {
                    Galaxy.router.push(`/?tool_id=${tool_id}&version=${tool_version}`);
                }
                self.removeOverlay();
            });
        });
    }

    var self = this;
    var parentElement = $(".full-content");
    self.showOverlay = showOverlay;
    self.removeOverlay = removeOverlay;

    // https://gist.github.com/jwilson8767/db379026efcbd932f64382db4b02853e
    function elementReady(selector) {
        return new Promise((resolve, reject) => {
            let el = document.querySelector(selector);
            if (el) {
                resolve(el);
            }
            new MutationObserver((mutationRecords, observer) => {
                // Query for elements matching the specified selector
                Array.from(document.querySelectorAll(selector)).forEach((element) => {
                    resolve(element);
                    //Once we have resolved we don't need the observer anymore.
                    observer.disconnect();
                });
            }).observe(document.documentElement, {
                childList: true,
                subtree: true,
            });
        });
    }

    elementReady("#gtn a").then((el) => {
        // External stuff may also have attached a click handler here (vue-based masthead)
        // replace with a clean copy of the node to remove all that cruft.
        clean = el.cloneNode(true);
        el.parentNode.replaceChild(clean, el);
        clean.addEventListener("click", (e) => {
            e.preventDefault();
            e.stopPropagation();
            return false;
            if (!gtnWebhookLoaded) {
                addIframe();
            }
            if ($(".gtn-screen-overlay").is(":visible")) {
                self.removeOverlay();
            } else {
                self.showOverlay();
            }
            return false;
        });
    });

    // Remove the overlay on escape button click
    document.addEventListener("keydown", function (e) {
        // Check for escape button - "27"
        if (e.which === 27 || e.keyCode === 27) {
            self.removeOverlay();
        }
    });
});
