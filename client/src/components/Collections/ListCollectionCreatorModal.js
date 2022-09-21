import _l from "utils/localization";
import Vue from "vue";
import { collectionCreatorModalSetup } from "./common/modal";

function listCollectionCreatorModal(elements, options) {
    options = options || {};
    options.title = _l("Create a collection from a list of datasets");
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
            },
        }).$mount(vm);
        return promise;
    });
}

/** Use a modal to create a list collection, then add it to the given history contents.
 *  @returns {Promise} resolved when the collection is added to the history.
 */
function createListCollection(contents, defaultHideSourceItems = true) {
    const elements = contents.toJSON();
    let copyElements;
    const promise = listCollectionCreatorModal(elements, {
        defaultHideSourceItems: defaultHideSourceItems,
        creationFn: function (elements, name, hideSourceItems) {
            elements = elements.map((element) => ({
                id: element.id,
                name: element.name,
                //TODO: this allows for list:list even if the filter above does not - reconcile
                src: element.src || (element.history_content_type == "dataset" ? "hda" : "hdca"),
            }));
            copyElements = !hideSourceItems;
            return contents.createHDCA(elements, "list", name, hideSourceItems, copyElements);
        },
    });
    return promise;
}
export default {
    listCollectionCreatorModal: listCollectionCreatorModal,
    createListCollection: createListCollection,
};
