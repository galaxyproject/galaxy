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

function listCollectionCreatorModal(elements, options) {
    options = options || {};
    options.title = _l("Create a collection from a list of datasets");
    const { deferred, showEl } = collectionCreatorModalSetup(options); // eslint-disable-line no-unused-vars
    return import(/* webpackChunkName: "ListCollectionCreator" */ "./ListCollectionCreator.vue").then((module) => {
        var listCollectionCreatorInstance = Vue.extend(module.default);
        var vm = document.createElement("div");
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
        return deferred;
    });
}

/** Use a modal to create a list collection, then add it to the given history contents.
 *  @returns {Deferred} resolved when the collection is added to the history.
 */
function createListCollection(contents, defaultHideSourceItems) {
    const elements = contents.toJSON();
    var copyElements;
    const promise = listCollectionCreatorModal(elements, {
        defaultHideSourceItems: defaultHideSourceItems,
        creationFn: function (elements, name, hideSourceItems) {
            elements = elements.map((element) => ({
                id: element.id,
                name: element.name,
                //TODO: this allows for list:list even if the filter above does not - reconcile
                src: element.history_content_type === "dataset" ? "hda" : "hdca",
            }));
            copyElements = !hideSourceItems;
            return contents.createHDCA(elements, "list", name, hideSourceItems, copyElements);
        },
    });
    return promise;
}
export default {
    // mixins: [CollectionCreatorModalMixin],
    listCollectionCreatorModal: listCollectionCreatorModal,
    createListCollection: createListCollection,
};