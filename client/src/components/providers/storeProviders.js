// Simple dataset provider, looks at api for result, renders to slot prop
import axios from "axios";
import { ref, watch, onMounted, computed } from "vue";
import { useDbKeyStore } from "stores/dbKeyStore";
import { useDatatypeStore } from "../../stores/datatypeStore";
import { prependPath } from "utils/redirect";

// Composable for simple provider functionality
export function useSimpleProvider(props, { slots }, urlGetter) {
    const loading = ref(false);
    const item = ref(null);

    async function load() {
        loading.value = true;
        const url = urlGetter ? urlGetter() : props.url;
        const { data } = await axios.get(url);
        item.value = data;
        loading.value = false;
    }

    async function save(newProps) {
        loading.value = true;
        const url = urlGetter ? urlGetter() : props.url;
        const { data } = await axios.put(url, newProps);
        item.value = data;
        loading.value = false;
    }

    // Watch for id changes
    watch(
        () => props.id,
        (newVal, oldVal) => {
            if (newVal !== oldVal) {
                load();
            }
        },
        { immediate: true }
    );

    // Return render function
    return () => {
        if (!slots.default) {
            return null;
        }
        return slots.default({
            loading: loading.value,
            item: item.value,
            save,
            result: item.value,
        });
    };
}

// For backwards compatibility, keep the mixin version temporarily
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
        const slot = this.$slots.default;
        if (slot) {
            return slot({
                loading: this.loading,
                item: this.item,
                save: this.save,
                result: this.item,
            });
        }
        return null;
    },
};

export const DbKeyProvider = {
    props: {
        id: null,
    },
    setup(props, { slots }) {
        const dbKeyStore = useDbKeyStore();
        const loading = ref(false);
        const item = ref(null);

        async function load() {
            loading.value = true;
            let dbKeys = dbKeyStore.getUploadDbKeys;
            if (dbKeys == null || dbKeys.length == 0) {
                await dbKeyStore.fetchUploadDbKeys();
                dbKeys = dbKeyStore.getUploadDbKeys;
            }
            item.value = dbKeys;
            loading.value = false;
        }

        async function save(newProps) {
            // DbKeyProvider doesn't support save
            console.warn("DbKeyProvider does not support save operation");
        }

        onMounted(() => {
            load();
        });

        return () => {
            if (!slots.default) {
                return null;
            }
            return slots.default({
                loading: loading.value,
                item: item.value,
                save,
                result: item.value,
            });
        };
    },
};

export const DatatypesProvider = {
    props: {
        id: null,
    },
    setup(props, { slots }) {
        const datatypeStore = useDatatypeStore();
        const loading = ref(false);
        const item = ref(null);

        async function load() {
            loading.value = true;
            let datatypes = datatypeStore.getUploadDatatypes;
            if (datatypes == null || datatypes.length == 0) {
                await datatypeStore.fetchUploadDatatypes();
                datatypes = datatypeStore.getUploadDatatypes;
            }
            item.value = datatypes;
            loading.value = false;
        }

        async function save(newProps) {
            // DatatypesProvider doesn't support save
            console.warn("DatatypesProvider does not support save operation");
        }

        onMounted(() => {
            load();
        });

        return () => {
            if (!slots.default) {
                return null;
            }
            return slots.default({
                loading: loading.value,
                item: item.value,
                save,
                result: item.value,
            });
        };
    },
};

export const SuitableConvertersProvider = {
    props: {
        id: { type: String, required: true },
    },
    setup(props, context) {
        const urlGetter = () => prependPath(`/api/dataset_collections/${props.id}/suitable_converters`);
        return useSimpleProvider(props, context, urlGetter);
    },
};

export const DatasetCollectionContentProvider = {
    props: {
        id: { type: String, required: true },
    },
    setup(props, context) {
        const urlGetter = () => prependPath(props.id);
        return useSimpleProvider(props, context, urlGetter);
    },
};

export const JobProvider = {
    props: {
        id: { type: String, required: true },
    },
    setup(props, context) {
        const urlGetter = () => prependPath(`api/jobs/${props.id}?full=true`);
        return useSimpleProvider(props, context, urlGetter);
    },
};

export const DatasetCollectionElementProvider = {
    props: {
        id: { type: String, required: true },
    },
    setup(props, context) {
        const urlGetter = () => prependPath(`api/dataset_collection_element/${props.id}`);
        return useSimpleProvider(props, context, urlGetter);
    },
};