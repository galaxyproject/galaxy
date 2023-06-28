(function () {
    function hideNewsOverlay() {
        const container = document.getElementById("news-container");
        if (container) {
            container.style.visibility = "hidden";
        }
    }

    function newsSeen() {
        // When it's seen, remove fa, add far.
        const newsIconSpan = document.querySelector("#news .fa-bullhorn");
        newsIconSpan.classList.remove("fa-fade");
        window.localStorage.setItem("galaxy-news-seen-release", Galaxy.config.version_major);
    }

    function newsUnseen() {
        // When there is news, remove far, add fa for (default -- same as fas) solid style.
        const newsIconSpan = document.querySelector("#news .fa-bullhorn");
        newsIconSpan.classList.add("fa-fade");
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

        // If we're at the 23.1 release candidate, we want to show the 23.0 release notes still.
        // This should be the last release using this hack -- new notification
        // system will provide notes moving forward

        if (currentGalaxyVersion == "23.1" && Galaxy.config.version_minor.startsWith("rc")) {
            currentGalaxyVersion = "23.0";
        }

        const releaseNotes = `https://docs.galaxyproject.org/en/latest/releases/${currentGalaxyVersion}_announce_user.html`;
        const lastSeenVersion = window.localStorage.getItem("galaxy-news-seen-release");
        // Check that they've seen the current version's release notes.
        if (lastSeenVersion != currentGalaxyVersion) {
            newsUnseen();
        } else {
            newsSeen();
        }

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
            newsSeen();
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
