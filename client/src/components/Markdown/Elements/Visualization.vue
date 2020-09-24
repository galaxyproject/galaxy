<template>
    <div class="w-50 p-2 float-left">
        <b-card body-class="embed-responsive embed-responsive-4by3">
            <div v-if="error" class="m-2">{{ error }}</div>
            <iframe v-else class="embed-responsive-item" :src="visualizationUrl" />
        </b-card>
    </div>
</template>

<script>
import axios from "axios";
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { getAppRoot } from "onload/loadConfig";

Vue.use(BootstrapVue);

export default {
    props: {
        args: {
            type: Object,
            default: null,
        },
    },
    data() {
        return {
            visualizationUrl: null,
            error: null,
        };
    },
    created() {
        this.getVisualization();
    },
    methods: {
        async getVisualization() {
            axios
                .get(`${getAppRoot()}api/plugins/${this.args.id}`)
                .then(({ data }) => {
                    this.visualizationUrl = `${data.href}?dataset_id=${this.args.history_dataset_id}`;
                })
                .catch((e) => {
                    this.error = `Failed to load Visualization '${this.args.id}'.`;
                });
        },
    },
};
</script>
