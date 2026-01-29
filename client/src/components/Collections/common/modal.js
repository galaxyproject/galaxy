import { getGalaxyInstance } from "app";
import UI_MODAL from "mvc/ui/ui-modal";
import _l from "utils/localization";

export function collectionCreatorModalSetup(options, Galaxy = null) {
    Galaxy = Galaxy || getGalaxyInstance();
    const modal = Galaxy.modal || new UI_MODAL.View();
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
        const close_event = options.closing_events === undefined || options.closing_events;
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
            xlarge: true,
            closing_events: close_event,
        });
    };
    return { promise, options, showEl };
}
