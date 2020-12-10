<script>
import CollectionCreatorModalMixin from "./common/CollectionCreatorModalMixin";
import _l from "utils/localization";
import Vue from "vue";
export default {
    mixins: [CollectionCreatorModalMixin],
    methods: {
        pairedListCollectionCreatorModal: function (elements, options) {
            options = options || {};
            options.title = _l("Create a collection of paired datasets");
            const { deferred, creatorOptions, showEl } = this.collectionCreatorModalSetup(options); // eslint-disable-line no-unused-vars
            return import(
                /* webpackChunkName: "PairedListCollectionCreator" */ "./PairedListCollectionCreator.vue"
            ).then((module) => {
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
            });
        },
        /** Use a modal to create a list collection, then add it to the given history contents.
         *  @returns {Deferred} resolved when the collection is added to the history.
         */
        createPairedListCollection: function (contents, defaultHideSourceItems) {
            const elements = contents.toJSON();
            var copyElements;
            const promise = this.pairedListCollectionCreatorModal(elements, {
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
        },
    },
};
</script>
