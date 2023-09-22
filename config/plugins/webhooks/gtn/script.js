(() => {
    let gtnWebhookLoaded = false;
    let lastUpdate = 0;
    const urlParams = new URLSearchParams(document.location.search);
    const autoLoadTutorial =
        urlParams.get("autoload_gtn_tutorial") === null ? "" : urlParams.get("autoload_gtn_tutorial");

    function removeOverlay() {
        const container = document.getElementById("gtn-container");
        if (container) {
            container.style.visibility = "hidden";
        }
    }

    function showOverlay() {
        document.getElementById("gtn-container").style.visibility = "visible";
    }

    function getIframeUrl() {
        let loc;
        try {
            loc = document.getElementById("gtn-embed").contentWindow.location.pathname;
        } catch (e) {
            loc = null;
        }
        return loc;
    }

    function getIframeScroll() {
        let loc;
        try {
            loc = parseInt(document.getElementById("gtn-embed").contentWindow.scrollY);
        } catch (e) {
            loc = 0;
        }
        return loc;
    }

    function persistLocation() {
        // Don't save every scroll event.
        const time = new Date().getTime();
        if (time - lastUpdate < 1000) {
            return;
        }
        lastUpdate = time;
        window.localStorage.setItem("gtn-in-galaxy", `${getIframeScroll()} ${getIframeUrl()}`);
    }

    function addIframe() {
        let url;
        let message;
        let onloadscroll;
        gtnWebhookLoaded = true;
        let storedData = false;
        let safe = false;

        // Test for the presence of /training-material/. If that is available we
        // can opt in the fancy click-to-run features. Otherwise we fallback to
        // displaying the real GTN.
        fetch("/training-material/")
            .then((response) => {
                if (!response.ok) {
                    url = `https://training.galaxyproject.org/training-material/${autoLoadTutorial}?utm_source=webhook&utm_medium=noproxy&utm_campaign=gxy`;
                    message = `
                        <span>
                            <a href="https://docs.galaxyproject.org/en/master/admin/special_topics/gtn.html">Click to run</a> unavailable.
                        </span>`;
                } else {
                    safe = true;

                    const storedLocation = window.localStorage.getItem("gtn-in-galaxy");
                    if (
                        storedLocation !== null &&
                        storedLocation.split(" ")[1] !== undefined &&
                        storedLocation.split(" ")[1].startsWith("/training-material/")
                    ) {
                        onloadscroll = storedLocation.split(" ")[0];
                        url = storedLocation.split(" ")[1];
                    } else {
                        url = `/training-material/${autoLoadTutorial}?utm_source=webhook&utm_medium=proxy&utm_campaign=gxy`;
                    }
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

                // Only setup the listener if it won't crash things.
                if (safe) {
                    // Listen to the scroll position
                    document.getElementById("gtn-embed").contentWindow.addEventListener("scroll", () => {
                        persistLocation();
                    });
                }

                // Depends on the iframe being present
                document.getElementById("gtn-embed").addEventListener("load", () => {
                    // Save our current location when possible
                    const gtnEmbed = document.getElementById("gtn-embed");
                    if (onloadscroll !== undefined) {
                        document.getElementById("gtn-embed").contentWindow.scrollTo(0, parseInt(onloadscroll));
                        onloadscroll = undefined;
                    }

                    if (safe) {
                        persistLocation();
                    }
                    // Add the class to the entire GTN page
                    document
                        .getElementById("gtn-embed")
                        .contentDocument.getElementsByTagName("body")[0]
                        .classList.add("galaxy-proxy-active");

                    const gtnToolElements = document
                        .getElementById("gtn-embed")
                        .contentDocument.querySelectorAll("span[data-tool],a[data-tool]");

                    // Buttonify
                    gtnToolElements.forEach(function (el) {
                        el.addEventListener("click", function (e) {
                            let target = e.target;

                            // Sometimes we get the i or the strong, not the parent.
                            if (e.target.tagName.toLowerCase() !== "span" && e.target.tagName.toLowerCase() !== "a") {
                                target = e.target.parentElement;
                            }

                            tool_id = target.dataset.tool;

                            if (tool_id === "upload1" || tool_id === "upload") {
                                document.getElementById("tool-panel-upload-button").click();
                            } else {
                                Galaxy.router.push({ path: `/?tool_id=${encodeURIComponent(tool_id)}` });
                            }
                            removeOverlay();
                        });
                    });

                    const gtnWorkflowElements = document
                        .getElementById("gtn-embed")
                        .contentDocument.querySelectorAll("span[data-workflow],a[data-workflow]");

                    // Buttonify
                    gtnWorkflowElements.forEach(function (el) {
                        el.addEventListener("click", (e) => {
                            let target = e.target;

                            // Sometimes we get the i or the strong, not the parent.
                            if (e.target.tagName.toLowerCase() !== "span" && e.target.tagName.toLowerCase() !== "a") {
                                target = e.target.parentElement;
                            }

                            trs_url = target.dataset.workflow;
                            Galaxy.router.push({
                                path: `/workflows/trs_import?trs_url=${encodeURIComponent(trs_url)}&run_form=true`,
                            });
                            removeOverlay();
                        });
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
                showOverlay();
            }
        });
        if (autoLoadTutorial) {
            clean.click();
        }
    });

    // Remove the overlay on escape button click
    document.addEventListener("keydown", (event) => {
        // Check for escape button - "Escape" (modern browsers), "27" (old browsers)
        if (event.key === "Escape" || event.keyCode === 27) {
            removeOverlay();
        }
    });
})();
