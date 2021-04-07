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
            default: true,
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
        /** return the concat'd longest common prefix and suffix from two strings */
        _naiveStartingAndEndingLCS: function (s1, s2) {
            var fwdLCS = "";
            var revLCS = "";
            var i = 0;
            var j = 0;
            while (i < s1.length && i < s2.length) {
                if (s1[i] !== s2[i]) {
                    break;
                }
                fwdLCS += s1[i];
                i += 1;
            }
            if (i === s1.length) {
                return s1;
            }
            if (i === s2.length) {
                return s2;
            }

            i = s1.length - 1;
            j = s2.length - 1;
            while (i >= 0 && j >= 0) {
                if (s1[i] !== s2[j]) {
                    break;
                }
                revLCS = [s1[i], revLCS].join("");
                i -= 1;
                j -= 1;
            }
            return fwdLCS + revLCS;
        },
    },
};
