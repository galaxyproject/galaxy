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
        /** Use a modal to create a list of pair collection, then add it to the given history contents.
         *  @returns {Deferred} resolved when the collection is added to the history.
         */
        createPairedListCollection: function (contents, defaultHideSourceItems) {
            const elements = contents.toJSON();
            // const copyElements = !defaultHideSourceItems;
            // const promise = this.pairedListCollectionCreatorModal(elements, {
            //     defaultHideSourceItems: defaultHideSourceItems,
            //     creationFn: function (elements, name, hideSourceItems) {
            //         elements = elements.map((element) => ({
            //             id: element.id,
            //             name: element.name,
            //             //TODO: this allows for list:list even if the filter above does not - reconcile
            //             src: element.history_content_type === "dataset" ? "hda" : "hdca",
            //         }));
            //         return contents.createHDCA(elements, "list", name, hideSourceItems, copyElements);
            //     },
            // });
            return this.pairedListCollectionCreatorModal(elements, {
                historyId: contents.historyId,
                defaultHideSourceItems: defaultHideSourceItems,
            });
        },
    },
};
</script>
