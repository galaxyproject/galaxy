// Simple dataset provider, looks at api for result, renders to slot prop
import axios from "axios";
import { mapActions, mapState } from "pinia";
import { useDbKeyStore } from "stores/dbKeyStore";
import { prependPath } from "utils/redirect";

import { useDatatypeStore } from "../../stores/datatypeStore";

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
            result: this.item,
        });
    },
};

export const DbKeyProvider = {
    mixins: [SimpleProviderMixin],
    props: {
        id: null,
    },
    async mounted() {
        await this.load();
    },
    methods: {
        ...mapActions(useDbKeyStore, ["fetchUploadDbKeys"]),
        async load() {
            this.loading = true;
            let dbKeys = this.getUploadDbKeys;
            if (dbKeys == null || dbKeys.length == 0) {
                await this.fetchUploadDbKeys();
                dbKeys = this.getUploadDbKeys;
            }
            this.item = dbKeys;
            this.loading = false;
        },
    },
    computed: {
        ...mapState(useDbKeyStore, ["getUploadDbKeys"]),
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
        ...mapActions(useDatatypeStore, ["fetchUploadDatatypes"]),
        async load() {
            this.loading = true;
            let datatypes = this.getUploadDatatypes;
            if (datatypes == null || datatypes.length == 0) {
                await this.fetchUploadDatatypes();
                datatypes = this.getUploadDatatypes;
            }
            this.item = datatypes;
            this.loading = false;
        },
    },
    computed: {
        ...mapState(useDatatypeStore, ["getUploadDatatypes"]),
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

export const DatasetCollectionElementProvider = {
    mixins: [SimpleProviderMixin],
    computed: {
        url() {
            return prependPath(`api/dataset_collection_element/${this.id}`);
        },
    },
};
