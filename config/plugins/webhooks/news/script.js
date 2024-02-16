(function () {
    function hideNewsOverlay() {
        const container = document.getElementById("news-container");
        if (container) {
            container.style.visibility = "hidden";
        }
    }

    function newsSeen(currentGalaxyVersion) {
        // When it's seen, remove the red indicator if it exists and store the current version.
        const newsIndicator = document.getElementById("news-indicator");
        if (newsIndicator) {
            newsIndicator.remove();
        }
        window.localStorage.setItem("galaxy-news-seen-release", currentGalaxyVersion);
    }

    function newsUnseen() {
        // When there is news, add an red indicator to the icon.
        const newsIconSpan = document.querySelector("#news .nav-link");
        newsIconSpan.insertAdjacentHTML("beforeend", '<span id="news-indicator"></span>');
    }

    /* The masthead icon may not exist yet when this webhook executes; we need this to wait for that to happen.
     * elementReady function from gist:
     * https://gist.github.com/jwilson8767/db379026efcbd932f64382db4b02853e
     */
    function elementReadyNews(selector) {
        return new Promise((resolve, reject) => {
            const el = document.querySelector(selector);
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

    elementReadyNews("#news a").then((el) => {
        // External stuff may also have attached a click handler here (vue-based masthead)
        // replace with a clean copy of the node to remove all that cruft.
        clean = el.cloneNode(true);
        el.parentNode.replaceChild(clean, el);

        let currentGalaxyVersion = Galaxy.config.version_major;
        const lastSeenVersion = window.localStorage.getItem("galaxy-news-seen-release");

        // If we're at a deployed release candidate, just mark it seen and show
        // the previous notes if someone clicks the link.  RC notes won't exist.
        if (Galaxy.config.version_minor.startsWith("rc")) {
            // If we, for whatever reason, need to do this again just add
            // another case here.  It's not worth parsing and doing version
            // math, and we should be able to drop preferring notifications
            // framework moving forward in 23.2
            if (currentGalaxyVersion == "23.1") {
                currentGalaxyVersion = "23.0";
            }
            newsSeen(currentGalaxyVersion);
        } else if (lastSeenVersion != currentGalaxyVersion) {
            newsUnseen();
        } else {
            newsSeen(currentGalaxyVersion);
        }

        const releaseNotes = `https://docs.galaxyproject.org/en/latest/releases/${currentGalaxyVersion}_announce_user.html`;

        clean.addEventListener("click", (e) => {
            e.preventDefault();
            e.stopPropagation();

            // If element doesn't exist, add it.
            if (document.getElementById("news-container") == null) {
                document.querySelector("body.full-content").insertAdjacentHTML(
                    "afterbegin",
                    `
                    <div id="news-container" style="visibility: hidden">
                        <div id="news-screen-overlay"></div>
                        <div id="news-screen">
                            <div id="news-header">
                                <iframe id="news-embed" src="${releaseNotes}" width="80%" height="80%"></iframe>
                            </div>
                        </div>
                    </div>`
                );
                // Clicking outside of GTN closes it
                document.getElementById("news-screen").addEventListener("click", () => {
                    hideNewsOverlay();
                });
            }
            document.getElementById("news-container").style.visibility = "visible";
            newsSeen(currentGalaxyVersion);
        });
    });

    // Remove the overlay on escape button click
    document.addEventListener("keydown", (e) => {
        // Check for escape button - "27"
        if (e.which === 27 || e.keyCode === 27) {
            hideNewsOverlay();
        }
    });
})();
