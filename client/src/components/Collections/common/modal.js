import _l from "utils/localization";
import Modal from "utils/modal";

export function collectionCreatorModalSetup(options, Galaxy = null) {
    const modal = new Modal();
    const promise = new Promise((then, reject) => {
        options.oncancel = function () {
            modal.hide();
            reject("cancelled");
        };
        options.oncreate = function (creator, response) {
            modal.hide();
            then(response);
        };
    });
    const showEl = function (el) {
        const closing_events = options.closing_events === undefined || options.closing_events;
        const title = options.title || _l("Create a collection");
        const titleSuffix = options.historyName ? `From history: <b>${options.historyName}</b>` : "";
        const titleHtml = `<div class='d-flex justify-content-between unselectable'>
                <span>${title}</span>
                <span>${titleSuffix}</span>
            </div>`;
        modal.show({
            title: titleHtml,
            body: el,
            width: "85%",
            height: "100%",
            closing_events: closing_events,
        });
    };
    return { promise, options, showEl };
}
