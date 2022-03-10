// Simple dataset provider, looks at api for result, renders to slot prop
import axios from "axios";
import { prependPath } from "utils/redirect";
import { mapCacheActions } from "vuex-cache";
import { mapActions, mapGetters } from "vuex";

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
                this.item = newItem;
            },
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

export const StoreProvider = (storeAction, storeGetter) => {
    return {
        watch: {
            $attrs() {
                this.load();
            },
        },
        async mounted() {
            await this.load();
        },
        created() {
            this.loading = true;
        },
        methods: {
            ...mapActions([storeAction]),
            async load() {
                this.loading = true;
                await this[storeAction]({ ...this.$attrs });
                this.loading = false;
            },
        },
        computed: {
            ...mapGetters([storeGetter]),
            result() {
                return this[storeGetter]();
            },
        },
        render() {
            return this.$scopedSlots.default({
                loading: this.loading,
                result: this.result,
            });
        },
    };
};

export const HistoryItemsProvider = StoreProvider("fetchHistoryItems", "getHistoryItems");
export const CollectionElementsProvider = StoreProvider("fetchCollectionElements", "getCollectionElements");
