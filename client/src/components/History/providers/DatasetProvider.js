// Simple dataset provider, looks at api for result, renders to slot prop
import Vue from "vue";
import axios from "axios";
import { prependPath } from "utils/redirect";

var SimpleProviderMixin = {
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
            const result = await axios.get(this.url);
            this.item = result.data;
            this.loading = false;
        },
        async save(newProps) {
            this.loading = true;
            const result = await axios.put(this.url, newProps);
            this.item = result.data;
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

var DatasetProvider = Vue.extend({
    mixins: [SimpleProviderMixin],
    computed: {
        url() {
            return prependPath(`api/datasets/${this.id}`);
        },
    },
});

var DatasetCollectionProvider = Vue.extend({
    mixins: [SimpleProviderMixin],
    computed: {
        url() {
            return prependPath(`api/dataset_collections/${this.id}?instance_type=history`);
        },
    },
});

var DatasetCollectionContentProvider = Vue.extend({
    mixins: [SimpleProviderMixin],
    computed: {
        url() {
            // ugh ...
            return prependPath(this.id);
        },
    },
});

var JobProvider = Vue.extend({
    mixins: [SimpleProviderMixin],
    computed: {
        url() {
            return prependPath(`api/jobs/${this.id}?full=true`);
        },
    },
});

export { DatasetProvider, DatasetCollectionProvider, DatasetCollectionContentProvider, JobProvider };
