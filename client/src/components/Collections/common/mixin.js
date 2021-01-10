import CollectionCreator from "./CollectionCreator";

export default {
    components: {
        CollectionCreator,
    },
    props: {
        initialElements: {
            required: true,
            type: Array,
        },
        creationFn: {
            type: Function,
            required: true,
        },
        /** fn to call when the cancel button is clicked (scoped to this) - if falsy, no btn is displayed */
        oncancel: {
            type: Function,
            required: true,
        },
        oncreate: {
            type: Function,
            required: true,
        },
        defaultHideSourceItems: {
            type: Boolean,
            required: false,
            default: false,
        },
    },
    data() {
        return {
            hideSourceItems: this.defaultHideSourceItems,
        };
    },
    methods: {
        onUpdateHideSourceItems(hideSourceItems) {
            this.hideSourceItems = hideSourceItems;
        },
    },
};
