import _l from "utils/localization";
import Vue from "vue";

import { orList } from "@/utils/strings";

import { collectionCreatorModalSetup } from "./common/modal";

function listCollectionCreatorModal(elements, options) {
    options = options || {};
    options.title = _l(
        `Create a collection from a list of ${options.fromSelection ? "selected" : ""} ${
            options.extensions?.length ? orList(options.extensions) : ""
        } datasets`
    );
    const { promise, showEl } = collectionCreatorModalSetup(options);
    return import(/* webpackChunkName: "ListCollectionCreator" */ "./ListCollectionCreator.vue").then((module) => {
        const listCollectionCreatorInstance = Vue.extend(module.default);
        const vm = document.createElement("div");
        showEl(vm);
        new listCollectionCreatorInstance({
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
    });
}

/** Use a modal to create a list collection, then add it to the given history contents.
 *  @returns {Promise} resolved when the collection is added to the history.
 */
function createListCollection(contents) {
    const elements = contents.toJSON();
    const promise = listCollectionCreatorModal(elements, {
        defaultHideSourceItems: contents.defaultHideSourceItems,
        fromSelection: contents.fromSelection,
        extensions: contents.extensions,
        creationFn: function (elements, name, hideSourceItems) {
            elements = elements.map((element) => ({
                id: element.id,
                name: element.name,
                //TODO: this allows for list:list even if the filter above does not - reconcile
                src: element.src || (element.history_content_type == "dataset" ? "hda" : "hdca"),
            }));
            return contents.createHDCA(elements, "list", name, hideSourceItems);
        },
    });
    return promise;
}
export default {
    listCollectionCreatorModal: listCollectionCreatorModal,
    createListCollection: createListCollection,
};
