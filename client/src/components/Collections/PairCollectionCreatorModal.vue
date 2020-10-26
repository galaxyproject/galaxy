<script>
import CollectionCreatorModalMixin from "./common/CollectionCreatorModalMixin";
import PairCollectionCreator from "./PairCollectionCreator";
import _l from "utils/localization";
export default {
    mixins: [CollectionCreatorModalMixin],
    methods: {
        pairCollectionCreatorModal: function (elements, options) {
            options = options || {};
            options.title = _l("Create a collection from a pair of datasets");
            const { deferred, creatorOptions, showEl } = this.collectionCreatorModalSetup(options); // eslint-disable-line no-unused-vars
            var vm = document.createElement("div");
            showEl(vm);
            new PairCollectionCreator({
                propsData: {
                    creationFn: options.creationFn,
                    oncancel: options.oncancel,
                    oncreate: options.oncreate,
                    //TODO : autoscollDist, highlightClr
                },
            }).$mount(vm);
            return deferred;
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
