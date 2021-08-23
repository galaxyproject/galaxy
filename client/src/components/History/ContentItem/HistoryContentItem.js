import ContentItem from "./ContentItem";

export default {
    mixins: [ContentItem],

    computed: {
        contentItemComponent() {
            if (this.item.id === undefined) {
                return "Placeholder";
            }
            const { history_content_type } = this.item;
            switch (history_content_type) {
                case "dataset":
                    if (this.item.tool_type == "interactive") {
                        return "InteractiveTool";
                    } else {
                        return "Dataset";
                    }
                case "dataset_collection":
                    return "DatasetCollection";
                default:
                    return "Placeholder";
            }
        },
    },
};
