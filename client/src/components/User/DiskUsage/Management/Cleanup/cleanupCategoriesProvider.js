import { cleanupCategories } from "./categories";
import { CleanupCategory } from "./model";

export default {
    created() {
        this.categories = this.loadCategories();
    },
    data() {
        return {
            categories: [],
        };
    },
    methods: {
        loadCategories() {
            return cleanupCategories.map((category) => new CleanupCategory(category));
        },
    },
    render() {
        return this.$scopedSlots.default({
            categories: this.categories,
        });
    },
};
