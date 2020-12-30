// Simple dataset provider, looks at api for result, renders to slot prop
import axios from "axios";
import { prependPath } from "utils/redirect";
import { mapCacheActions } from "vuex-cache";
import { mapGetters } from "vuex";

export const SimpleProviderMixin = {
    props: {
        id: { type: String, required: true },
    },
    data() {
        return {
            loading: false,
            item: null,
        };
    },
    watch: {
        id: {
            immediate: true,
            handler(newVal, oldVal) {
                if (newVal !== oldVal) {
                    this.load();
                }
            },
        },
    },
    methods: {
        async load() {
            this.loading = true;
            const { data } = await axios.get(this.url);
            this.item = data;
            this.loading = false;
        },
        async save(newProps) {
            this.loading = true;
            const { data } = await axios.put(this.url, newProps);
            this.item = data;
            this.loading = false;
        },
    },
    render() {
        return this.$scopedSlots.default({
            loading: this.loading,
            item: this.item,
            save: this.save,
        });
    },
};

export const StoreProviderMixin = {
    computed: {
        storeItem() {
            throw new Error("define me");
        },
    },
    watch: {
        storeItem: {
            handler(newItem, oldItem) {
                console.log("Updating item to", newItem);
                this.item = newItem;
            },
        },
    },
};

export const DatasetProvider = {
    mixins: [SimpleProviderMixin, StoreProviderMixin],
    methods: {
        ...mapCacheActions("datasets", ["fetchDataset"]),
        async load() {
            this.loading = true;
            this.item = await this.fetchDataset(this.id);
            this.loading = false;
        },
    },
    computed: {
        ...mapGetters("datasets", ["getDatasetById"]),
        storeItem() {
            return this.getDatasetById(this.id);
        },
    },
};

export const DatasetCollectionProvider = {
    mixins: [SimpleProviderMixin, StoreProviderMixin],
    methods: {
        ...mapCacheActions("datasetCollections", ["fetchDatasetCollection"]),
        async load() {
            this.loading = true;
            this.item = await this.fetchDatasetCollection(this.id);
            this.loading = false;
        },
    },
    computed: {
        ...mapGetters("datasetCollections", ["getDatasetCollectionById"]),
        storeItem() {
            return this.getDatasetCollectionById(this.id);
        },
    },
};

export const DatasetCollectionContentProvider = {
    mixins: [SimpleProviderMixin],
    computed: {
        url() {
            // ugh ...
            return prependPath(this.id);
        },
    },
};

export const JobProvider = {
    mixins: [SimpleProviderMixin],
    computed: {
        url() {
            return prependPath(`api/jobs/${this.id}?full=true`);
        },
    },
};
