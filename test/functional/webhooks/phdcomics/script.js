// Injected by the webhook framework (see appendScriptStyle in client/src/utils/utils.ts).
// Runs in the global page scope wrapped in an IIFE, so it must be self-contained
// vanilla JS -- Backbone, underscore and jQuery are no longer available globals.
const root = typeof Galaxy !== "undefined" && Galaxy.root ? Galaxy.root : "/";
const container = document.getElementById("phdcomics");

if (container) {
    container.innerHTML =
        '<div id="phdcomics-header">' +
        '<div id="phdcomics-name">PHD Comics</div>' +
        '<button id="phdcomics-random" type="button">Random</button>' +
        "</div>" +
        '<div id="phdcomics-img"></div>';

    const imgContainer = document.getElementById("phdcomics-img");

    async function loadRandomComic() {
        imgContainer.innerHTML = '<div id="phdcomics-loader"></div>';
        const url = `${root}api/webhooks/phdcomics/data`;
        try {
            const response = await fetch(url);
            const data = await response.json();
            if (data.success) {
                const img = document.createElement("img");
                img.src = data.src;
                imgContainer.replaceChildren(img);
            } else {
                console.error(`[phdcomics webhook] "${url}":\n${data.error}`);
            }
        } catch (e) {
            console.error(`[phdcomics webhook] request to "${url}" failed`, e);
        }
    }

    document.getElementById("phdcomics-random").addEventListener("click", loadRandomComic);
    loadRandomComic();
}
