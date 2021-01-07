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

function pairedListCollectionCreatorModal(elements, options) {
    options = options || {};
    options.title = _l("Create a collection of paired datasets");
    const { deferred, showEl } = collectionCreatorModalSetup(options); // eslint-disable-line no-unused-vars
    return import(/* webpackChunkName: "PairedListCollectionCreator" */ "./PairedListCollectionCreator.vue").then(
        (module) => {
            var pairedListCollectionCreatorInstance = Vue.extend(module.default);
            var vm = document.createElement("div");
            showEl(vm);
            new pairedListCollectionCreatorInstance({
                propsData: {
                    initialElements: elements,
                    creationFn: options.creationFn,
                    oncancel: options.oncancel,
                    oncreate: options.oncreate,
                    defaultHideSourceItems: options.defaultHideSourceItems,
                },
            }).$mount(vm);
            return deferred;
        }
    );
}

/** Use a modal to create a list collection, then add it to the given history contents.
 *  @returns {Deferred} resolved when the collection is added to the history.
 */
function createPairedListCollection(contents, defaultHideSourceItems) {
    const elements = contents.toJSON();
    var copyElements;
    const promise = pairedListCollectionCreatorModal(elements, {
        defaultHideSourceItems: defaultHideSourceItems,
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
            copyElements = !hideSourceItems;
            return contents.createHDCA(elements, "list:paired", name, hideSourceItems, copyElements);
        },
    });
    return promise;
}
export default {
    pairedListCollectionCreatorModal: pairedListCollectionCreatorModal,
    createPairedListCollection: createPairedListCollection,
};
