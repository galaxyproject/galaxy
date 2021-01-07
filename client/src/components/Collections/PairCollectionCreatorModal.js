import jQuery from "jquery";
import { getGalaxyInstance } from "app";
import UI_MODAL from "mvc/ui/ui-modal";
import _l from "utils/localization";
import Vue from "vue";

function collectionCreatorModalSetup(options) {
    const deferred = jQuery.Deferred();
    const Galaxy = getGalaxyInstance();
    const modal = Galaxy.modal || new UI_MODAL.View();
    options.oncancel = function () {
        modal.hide();
        deferred.reject("cancelled");
    };
    options.oncreate = function (creator, response) {
        modal.hide();
        deferred.resolve(response);
    };
    const showEl = function (el) {
        modal.show({
            title: options.title || _l("Create a collection"),
            body: el,
            width: "85%",
            height: "100%",
            xlarge: true,
            closing_events: true,
        });
    };
    return { deferred, showEl };
}

function pairCollectionCreatorModal(elements, options) {
    options = options || {};
    options.title = _l("Create a collection from a pair of datasets");
    const { deferred, showEl } = collectionCreatorModalSetup(options); // eslint-disable-line no-unused-vars
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
        return deferred;
    });
}
function createPairCollection(contents, defaultHideSourceItems) {
    var elements = contents.toJSON();
    var copyElements;
    var promise = pairCollectionCreatorModal(elements, {
        defaultHideSourceItems: defaultHideSourceItems,
        creationFn: function (elements, name, hideSourceItems) {
            elements = [
                { name: "forward", src: "hda", id: elements[0].id },
                { name: "reverse", src: "hda", id: elements[1].id },
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