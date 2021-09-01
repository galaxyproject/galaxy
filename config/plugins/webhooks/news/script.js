function removeNewsOverlay() {
  document.getElementById("news-container").style.visibility = "hidden";
}

function showNewsOverlay() {
  document.getElementById("news-container").style.visibility = "visible";
  newsSeen();
}

function newsSeen() {
  var el = document.getElementById("news-unseen-pip");
  el.parentNode.removeChild(el);
  window.localStorage.setItem(
    "galaxy-news-seen-release",
    Galaxy.config.version_major
  );
}

function newsUnseen() {
  let econtainer = document.getElementById("news").children[0];
  econtainer.insertAdjacentHTML(
    "beforeend",
    `
        <span id="news-unseen-pip" class="nav-note fa fa-circle"></span>
        `
  );
}

function addNewsIframe() {
  let currentGalaxyVersion = Galaxy.config.version_major;
  let releaseNotes = `https://docs.galaxyproject.org/en/master/releases/${currentGalaxyVersion}_announce_user.html`;
  let lastSeenVersion = window.localStorage.getItem("galaxy-news-seen-release");
  // Check that they've seen the current version's release notes.
  if (lastSeenVersion != currentGalaxyVersion) {
    newsUnseen();
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
    let el = document.querySelector(selector);
    if (el) {
      resolve(el);
    }
    new MutationObserver((mutationRecords, observer) => {
      // Query for elements matching the specified selector
      Array.from(document.querySelectorAll(selector)).forEach(element => {
        resolve(element);
        //Once we have resolved we don't need the observer anymore.
        observer.disconnect();
      });
    }).observe(document.documentElement, {
      childList: true,
      subtree: true
    });
  });
}

elementReadyNews("#news a").then(el => {
  // External stuff may also have attached a click handler here (vue-based masthead)
  // replace with a clean copy of the node to remove all that cruft.
  clean = el.cloneNode(true);
  el.parentNode.replaceChild(clean, el);

  // This gets added by default.
  addNewsIframe();

  clean.addEventListener("click", e => {
    e.preventDefault();
    e.stopPropagation();
    showNewsOverlay();
  });
});

// Remove the overlay on escape button click
document.addEventListener("keydown", e => {
  // Check for escape button - "27"
  if (e.which === 27 || e.keyCode === 27) {
    removeNewsOverlay();
  }
});
