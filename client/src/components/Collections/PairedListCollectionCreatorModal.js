import _l from "utils/localization";
import Vue from "vue";

import { orList } from "@/utils/strings";

import { collectionCreatorModalSetup } from "./common/modal";

import PairedListCollectionCreator from "./PairedListCollectionCreator.vue";

function pairedListCollectionCreatorModal(elements, options) {
    options = options || {};
    options.title = _l(
        `Create a collection of ${options.fromSelection ? "selected" : ""} ${
            options.extensions?.length ? orList(options.extensions) : ""
        } dataset pairs`
    );
    const { promise, showEl } = collectionCreatorModalSetup(options);
    var pairedListCollectionCreatorInstance = Vue.extend(PairedListCollectionCreator);
    var vm = document.createElement("div");
    showEl(vm);
    new pairedListCollectionCreatorInstance({
        propsData: {
            initialElements: elements,
            creationFn: options.creationFn,
            oncancel: options.oncancel,
            oncreate: options.oncreate,
            defaultHideSourceItems: options.defaultHideSourceItems,
            fromSelection: options.fromSelection,
            extensions: options.extensions,
        },
    }).$mount(vm);
    return promise;
}

/** Use a modal to create a list collection, then add it to the given history contents.
 *  @returns {Promise} resolved when the collection is added to the history.
 */
function createPairedListCollection(contents) {
    const elements = contents.toJSON();
    const promise = pairedListCollectionCreatorModal(elements, {
        defaultHideSourceItems: contents.defaultHideSourceItems,
        fromSelection: contents.fromSelection,
        extensions: contents.extensions,
        historyName: contents.historyName,
        creationFn: function (elements, name, hideSourceItems) {
            elements = elements.map((pair) => ({
                collection_type: "paired",
                src: "new_collection",
                name: pair.name,
                element_identifiers: [
                    {
                        name: "forward",
                        id: pair.forward.id,
                        src: pair.forward.src || "hda",
                    },
                    {
                        name: "reverse",
                        id: pair.reverse.id,
                        src: pair.reverse.src || "hda",
                    },
                ],
            }));
            return contents.createHDCA(elements, "list:paired", name, hideSourceItems);
        },
    });
    return promise;
}
export default {
    pairedListCollectionCreatorModal: pairedListCollectionCreatorModal,
    createPairedListCollection: createPairedListCollection,
};
