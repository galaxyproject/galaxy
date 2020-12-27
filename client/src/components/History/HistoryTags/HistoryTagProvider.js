import { updateHistoryFields } from "../model/queries";
import { debounce } from "lodash";

export default {
    props: {
        history: { type: Object, required: true },
        debounceTime: { type: Number, required: false, default: 500 },
    },

    data() {
        return {
            loading: false,
            items: new Set(this.history?.tags || []),
        };
    },

    computed: {
        tags() {
            return Array.from(this.items);
        },
    },

    methods: {
        async saveTag(tag) {
            if (!tag) return;
            const newTags = new Set(this.items);
            newTags.add(tag);
            await this.saveTags(newTags);
        },
        async deleteTag(doomedTag) {
            if (!doomedTag) return;
            const newTags = new Set(this.items);
            newTags.delete(doomedTag);
            await this.saveTags(newTags);
        },
        async saveTags(rawTags) {
            this.loading = true;
            const tags = Array.from(rawTags);
            const newHistory = await updateHistoryFields(this.history, { tags });
            this.items = new Set(newHistory.tags || []);
            this.loading = false;
        },
    },

    created() {
        this.saveTags = debounce(this.saveTags, this.debounceTime);
    },

    render() {
        return this.$scopedSlots.default({
            loading: this.loading,
            tags: this.tags,
            saveTag: this.saveTag,
            deleteTag: this.deleteTag,
            saveTags: this.saveTags,
        });
    },
};
