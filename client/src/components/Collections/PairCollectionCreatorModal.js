import _l from "utils/localization";
import Vue from "vue";
import { collectionCreatorModalSetup } from "./common/modal";

function pairCollectionCreatorModal(elements, options) {
    options = options || {};
    options.title = _l("Create a collection from a pair of datasets");
    const { promise, showEl } = collectionCreatorModalSetup(options);
    return import(/* webpackChunkName: "PairCollectionCreator" */ "./PairCollectionCreator.vue").then((module) => {
        var pairCollectionCreatorInstance = Vue.extend(module.default);
        var vm = document.createElement("div");
        showEl(vm);
        new pairCollectionCreatorInstance({
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
function createPairCollection(contents, defaultHideSourceItems = true) {
    var elements = contents.toJSON();
    var copyElements;
    var promise = pairCollectionCreatorModal(elements, {
        defaultHideSourceItems: defaultHideSourceItems,
        creationFn: function (elements, name, hideSourceItems) {
            elements = [
                { name: "forward", src: elements[0].src || "hda", id: elements[0].id },
                { name: "reverse", src: elements[1].src || "hda", id: elements[1].id },
            ];
            copyElements = !hideSourceItems;
            return contents.createHDCA(elements, "paired", name, hideSourceItems, copyElements);
        },
    });
    return promise;
}
export default {
    pairCollectionCreatorModal: pairCollectionCreatorModal,
    createPairCollection: createPairCollection,
};
