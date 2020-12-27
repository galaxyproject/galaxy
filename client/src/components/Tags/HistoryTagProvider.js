import { ListStorage } from "utils/ListStorage";

const loadTags = async(id) => {
    console.log("loading history tags");
    return [];
};

const saveTag = async (id, tag) => {
    console.log("saving tag to server", id, tag);
    return tag;
};

const deleteTag = async (id, doomedTag) => {
    console.log("deleting tag from server", id, doomedTag);
    return true;
};

const loadAutocompleteOptions = async (id) => {
    console.log("getting auto complete stuff");
    return [];
};

export default {

    props: {
        historyId: { type: String, required: true },
    },

    data() {
        return {
            loading: true,
            tems: new ListStorage((item) => item.id),
            autocompleteOptions: [],
        };
    },

    computed: {
        tags() {
            return Array.from(this.items)
        },
    },

    async created() {
        this.autocompleteOptions = await loadAutocompleteOptions(this.id);
        const initialtags = await loadTags(this.id);
        this.items = this.items.bulkLoad(initialtags);
        this.loading = false;
    },

    methods: {

        async saveTag(newTag) {
            this.loading = true;
            try {
                const savedTag = await saveTag(this.historyId, newTag);
                this.items = this.items.add(savedTag);
            } catch (err) {
                console.warn("couldn't save tag", err, newTag);
            } finally {
                this.loading = false;
            }
        },

        async deleteTag(doomedTag) {
            this.loading = true;
            try {
                await deleteTag(this.historyId, doomedTag);
                this.items = this.items.remove(doomedTag);
            } catch (err) {
                console.warn("couldn't delete tag", err, doomedTag);
            } finally {
                this.loading = false;
            }
        },

    },

    render() {
        return this.$scopedSlots.default({
            loading: this.loading,
            tags: this.tags,
            autocompleteOptions: this.autocompleteOptions,
            saveTag: this.saveTag,
            deleteTag: this.deleteTag,
        });
    },
};
