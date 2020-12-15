<script>
import CollectionCreatorModalMixin from "./common/CollectionCreatorModalMixin";
import _l from "utils/localization";
import Vue from "vue";
export default {
    mixins: [CollectionCreatorModalMixin],
    methods: {
        listCollectionCreatorModal: function (elements, options) {
            options = options || {};
            options.title = _l("Create a collection from a list of datasets");
            const { deferred, creatorOptions, showEl } = this.collectionCreatorModalSetup(options); // eslint-disable-line no-unused-vars
            return import(/* webpackChunkName: "ListCollectionCreator" */ "./ListCollectionCreator.vue").then(
                (module) => {
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
                }
            );
        },
        /** Use a modal to create a list collection, then add it to the given history contents.
         *  @returns {Deferred} resolved when the collection is added to the history.
         */
        createListCollection: function (contents, defaultHideSourceItems) {
            const elements = contents.toJSON();
            var copyElements;
            const promise = this.listCollectionCreatorModal(elements, {
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
        },
    },
};
</script>
