var gtnWebhookLoaded = false;

function removeOverlay() {
    document.getElementById("gtn-container").classList.add("d-none");
}

function addIframe() {
    let url, message;
    gtnWebhookLoaded = true;

    // Test for the presence of /training-material/. If that is available we
    // can opt in the fancy click-to-run features. Otherwise we fallback to
    // displaying the real GTN.
    fetch("/training-material/")
        .then((response) => {
            if (!response.ok) {
                url = "https://training.galaxyproject.org/training-material/";
                message = `
                        <span>
                            <a href="https://docs.galaxyproject.org/en/master/admin/special_topics/gtn.html">Click to run</a> unavailable.
                        </span>`;
            } else {
                url = "/training-material/";
                message = "";
            }
        })
        .then(() => {
            document.querySelector("body.full-content").insertAdjacentHTML(
                "afterbegin",
                `
                    <div id="gtn-container">
                        <div id="gtn-screen-overlay"></div>
                        <div id="gtn-screen">
                            <div id="gtn-header">
                                <iframe id="gtn-embed" src="${url}" width="80%" height="80%"></iframe>
                                ${message}
                            </div>
                        </div>
                    </div>`
            );

            // Clicking outside of GTN closes it
            document.getElementById("gtn-screen").addEventListener("click", () => {
                removeOverlay();
            });

            // Depends on the iframe being present
            document.getElementById("gtn-embed").addEventListener("load", () => {
                var gtn_tools = $("#gtn-embed").contents().find("span[data-tool]");
                // Buttonify
                gtn_tools.addClass("galaxy-proxy-active");

                gtn_tools.click((e) => {
                    var target = e.target;

                    // Sometimes we get the i or the strong, not the parent.
                    if (e.target.tagName.toLowerCase() !== "span") {
                        target = e.target.parentElement;
                    }

                    tool_id = $(target).data("tool");

                    if (tool_id === "upload1" || tool_id === "upload") {
                        Galaxy.upload.show();
                    } else {
                        Galaxy.router.push(`?tool_id=${tool_id}`);
                    }
                    removeOverlay();
                });
            });
        });
}
/* The masthead icon may not exist yet when this webhook executes; we need this to wait for that to happen.
 * elementReady function from gist:
 * https://gist.github.com/jwilson8767/db379026efcbd932f64382db4b02853e
 */
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
        if (!gtnWebhookLoaded) {
            addIframe();
        } else {
            document.getElementById("gtn-container").classList.toggle("d-none");
        }
    });
});

// Remove the overlay on escape button click
document.addEventListener("keydown", (e) => {
    // Check for escape button - "27"
    if (e.which === 27 || e.keyCode === 27) {
        removeOverlay();
    }
});
