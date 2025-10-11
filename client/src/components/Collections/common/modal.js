import _l from "utils/localization";
import Modal from "utils/modal";

export function collectionCreatorModalSetup(options) {
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
        });
    };
    return { promise, options, showEl };
}
