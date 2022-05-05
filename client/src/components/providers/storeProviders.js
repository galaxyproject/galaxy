// Simple dataset provider, looks at api for result, renders to slot prop
import axios from "axios";
import { prependPath } from "utils/redirect";
import { mapActions, mapGetters } from "vuex";
import { mapCacheActions } from "vuex-cache";

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

export const GenomeProvider = {
    mixins: [SimpleProviderMixin],
    props: {
        id: null,
    },
    async mounted() {
        await this.load();
    },
    methods: {
        ...mapCacheActions(["fetchUploadGenomes"]),
        async load() {
            this.loading = true;
            let genomes = this.getUploadGenomes();
            if (genomes == null || genomes.length == 0) {
                await this.fetchUploadGenomes();
                genomes = this.getUploadGenomes();
            }
            this.item = genomes;
            this.loading = false;
        },
    },
    computed: {
        ...mapGetters(["getUploadGenomes"]),
    },
};

export const DatatypesProvider = {
    mixins: [SimpleProviderMixin],
    props: {
        id: null,
    },
    async mounted() {
        await this.load();
    },
    methods: {
        ...mapCacheActions(["fetchUploadDatatypes"]),
        async load() {
            this.loading = true;
            let datatypes = this.getUploadDatatypes();
            if (datatypes == null || datatypes.length == 0) {
                await this.fetchUploadDatatypes();
                datatypes = this.getUploadDatatypes();
            }
            this.item = datatypes;
            this.loading = false;
        },
    },
    computed: {
        ...mapGetters(["getUploadDatatypes"]),
    },
};

export const SuitableConvertersProvider = {
    mixins: [SimpleProviderMixin],
    computed: {
        url() {
            return prependPath(`/api/dataset_collections/${this.id}/suitable_converters`);
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

/**
 * Provider component interface to the actual stores i.e. history items and collection elements stores.
 * @param {String} storeAction The store action is executed when the consuming component e.g. the history panel, changes the provider props.
 * @param {String} storeGetter The store getter passes its result to the slot of the corresponding provider.
 * @param {String} storeCountGetter The query stats store getter passes its matches counts to the slot of the corresponding provider.
 */
export const StoreProvider = (storeAction, storeGetter, storeCountGetter = undefined) => {
    return {
        watch: {
            $attrs(newVal, oldVal) {
                if (JSON.stringify(newVal) != JSON.stringify(oldVal)) {
                    this.load();
                }
            },
        },
        data() {
            return {
                loading: false,
                error: null,
            };
        },
        created() {
            this.load();
        },
        computed: {
            ...mapGetters([storeGetter, storeCountGetter]),
            attributes() {
                return this.toCamelCase(this.$attrs);
            },
            result() {
                return this[storeGetter](this.attributes);
            },
            count() {
                return storeCountGetter ? this[storeCountGetter]() : undefined;
            },
        },
        render() {
            return this.$scopedSlots.default({
                error: this.error,
                loading: this.loading,
                result: this.result,
                count: this.count,
            });
        },
        methods: {
            ...mapActions([storeAction]),
            async load() {
                this.loading = true;
                try {
                    await this[storeAction](this.attributes);
                    this.error = null;
                    this.loading = false;
                } catch (error) {
                    this.error = error;
                    this.loading = false;
                }
            },
            toCamelCase(attributes) {
                const result = {};
                for (const key in attributes) {
                    const newKey = key.replace(/-./g, (x) => x[1].toUpperCase());
                    result[newKey] = attributes[key];
                }
                return result;
            },
        },
    };
};

export const DatasetProvider = StoreProvider("fetchDataset", "getDataset");
export const CollectionElementsProvider = StoreProvider("fetchCollectionElements", "getCollectionElements");
export const HistoryItemsProvider = StoreProvider("fetchHistoryItems", "getHistoryItems", "getTotalMatchesCount");
