<script>
import CollectionCreatorModalMixin from "./common/CollectionCreatorModalMixin";
import _l from "utils/localization";
import Vue from "vue";
export default {
    mixins: [CollectionCreatorModalMixin],
    methods: {
        pairCollectionCreatorModal: function (elements, options) {
            options = options || {};
            options.title = _l("Create a collection from a pair of datasets");
            const { deferred, creatorOptions, showEl } = this.collectionCreatorModalSetup(options); // eslint-disable-line no-unused-vars
            return import(/* webpackChunkName: "PairCollectionCreator" */ "./PairCollectionCreator.vue").then(
                (module) => {
                    var pairCollectionCreatorInstance = Vue.extend(module.default);
                    var vm = document.createElement("div");
                    showEl(vm);
                    new pairCollectionCreatorInstance({
                        propsData: {
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
        createPairCollection: function (contents, defaultHideSourceItems) {
            var elements = contents.toJSON();
            const copyElements = !defaultHideSourceItems;
            var promise = this.pairCollectionCreatorModal(elements, {
                defaultHideSourceItems: defaultHideSourceItems,
                creationFn: function (elements, name, hideSourceItems) {
                    elements = [
                        { name: "forward", src: "hda", id: elements[0].id },
                        { name: "reverse", src: "hda", id: elements[1].id },
                    ];
                    return contents.createHDCA(elements, "paired", name, hideSourceItems, copyElements);
                },
            });
            return promise;
        },
    },
};
</script>
