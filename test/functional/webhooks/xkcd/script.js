// Injected by the webhook framework (see appendScriptStyle in client/src/utils/utils.ts).
// Runs in the global page scope wrapped in an IIFE, so it must be self-contained
// vanilla JS -- Backbone, underscore and jQuery are no longer available globals.
// The comic is fetched through the server-side helper (__init__.py) because the
// xkcd JSON API sends no CORS headers and is only served over HTTPS.
const root = typeof Galaxy !== "undefined" && Galaxy.root ? Galaxy.root : "/";
const container = document.getElementById("xkcd");

if (container) {
    container.innerHTML =
        '<div id="xkcd-header">' +
        '<div id="xkcd-name">xkcd</div>' +
        '<button id="xkcd-random" type="button">Random</button>' +
        "</div>" +
        '<div id="xkcd-img"></div>';

    const imgContainer = document.getElementById("xkcd-img");

    async function loadRandomComic() {
        imgContainer.innerHTML = '<div id="xkcd-loader"></div>';
        const url = `${root}api/webhooks/xkcd/data`;
        try {
            const response = await fetch(url);
            const data = await response.json();
            if (data.success) {
                const img = document.createElement("img");
                img.src = data.comic.img;
                img.alt = data.comic.alt;
                img.title = data.comic.title;
                imgContainer.replaceChildren(img);
            } else {
                console.error(`[xkcd webhook] "${url}":\n${data.error}`);
            }
        } catch (e) {
            console.error(`[xkcd webhook] request to "${url}" failed`, e);
        }
    }

    document.getElementById("xkcd-random").addEventListener("click", loadRandomComic);
    loadRandomComic();
}
