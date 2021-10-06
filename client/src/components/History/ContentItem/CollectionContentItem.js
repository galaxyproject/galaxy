import ContentItem from "./ContentItem";

export default {
    mixins: [ContentItem],

    computed: {
        contentItemComponent() {
            const { history_content_type } = this.item;
            switch (history_content_type) {
                case "dataset":
                    return "Subdataset";
                case "dataset_collection":
                    return "Subcollection";
                default:
                    return "Placeholder";
            }
        },
    },
};
