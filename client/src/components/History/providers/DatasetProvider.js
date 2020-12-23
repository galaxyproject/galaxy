// Simple dataset provider, looks at api for result, renders to slot prop
import Vue from "vue";
import axios from "axios";
import { prependPath } from "utils/redirect";

import { mapCacheActions } from "vuex-cache";
import { mapGetters } from "vuex";

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

var DatasetProvider = Vue.extend({
    mixins: [SimpleProviderMixin],
    methods: {
        ...mapCacheActions("datasets", ["fetchDataset"]),
        async load() {
            this.loading = true;
            this.item = await this.fetchDataset(this.id);
            this.loading = false;
        },
    },
    watch: {
        dataset: {
            handler(newState, oldState) {
                this.item = newState;
            },
        },
    },
    computed: {
        ...mapGetters("datasets", ["getDatasetById"]),
        dataset() {
            return this.getDatasetById(this.id);
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
