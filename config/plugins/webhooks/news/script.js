function removeNewsOverlay() {
    document.getElementById("news-container").style.visibility = "hidden";
}

function showNewsOverlay() {
    document.getElementById("news-container").style.visibility = "visible";
    newsSeen();
}

function newsSeen() {
    // When it's seen, remove fa, add far.
    const newsIconSpan = document.querySelector("#news .fa-bell");
    newsIconSpan.classList.remove("fa");
    newsIconSpan.classList.add("far");
    window.localStorage.setItem("galaxy-news-seen-release", Galaxy.config.version_major);
}

function newsUnseen() {
    // When there is news, remove far, add fa for (default -- same as fas) solid style.
    const newsIconSpan = document.querySelector("#news .fa-bell");
    newsIconSpan.classList.remove("far");
    newsIconSpan.classList.add("fa");
}

function addNewsIframe() {
    var currentGalaxyVersion = Galaxy.config.version_major;

    // TODO/@hexylena: By 21.01 we will have a proper solution for this. For
    // now we'll hardcode the version users 'see'. @hexylena will remove this
    // code when she writes the user-facing release notes, and then will file
    // an issue for how we'll fix this properly.
    if (currentGalaxyVersion == "22.01") {
        currentGalaxyVersion = "21.09";
    }

    const releaseNotes = `https://docs.galaxyproject.org/en/latest/releases/${currentGalaxyVersion}_announce_user.html`;
    const lastSeenVersion = window.localStorage.getItem("galaxy-news-seen-release");
    // Check that they've seen the current version's release notes.
    if (lastSeenVersion != currentGalaxyVersion) {
        newsUnseen();
    } else {
        newsSeen();
    }

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
        removeNewsOverlay();
    });
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

    // This gets added by default.
    addNewsIframe();

    clean.addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        showNewsOverlay();
    });
});

// Remove the overlay on escape button click
document.addEventListener("keydown", (e) => {
    // Check for escape button - "27"
    if (e.which === 27 || e.keyCode === 27) {
        removeNewsOverlay();
    }
});
