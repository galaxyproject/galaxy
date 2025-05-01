<template>
    <b-card body-class="embed-responsive embed-responsive-4by3">
        <LoadingSpan v-if="loading" class="m-2" message="正在加载可视化" />
        <div v-else-if="error" class="m-2">{{ error }}</div>
        <iframe v-else title="Galaxy 可视化框架" class="embed-responsive-item" :src="visualizationUrl" />
    </b-card>
</template>

<script>
import axios from "axios";
import BootstrapVue from "bootstrap-vue";
import LoadingSpan from "components/LoadingSpan";
import { getAppRoot } from "onload/loadConfig";
import Vue from "vue";

Vue.use(BootstrapVue);

export default {
    components: {
        LoadingSpan,
    },
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
            loading: true,
        };
    },
    created() {
        this.getVisualization();
    },
    methods: {
        async getVisualization() {
            axios
                .get(`${getAppRoot()}api/plugins/${this.args.visualization_id}`)
                .then(({ data }) => {
                    const params = Object.entries(this.args)
                        .map((pair) => pair.map(encodeURIComponent).join("="))
                        .join("&");
                    this.visualizationUrl = `${data.href}?dataset_id=${this.args.history_dataset_id}&${params}`;
                    this.loading = false;
                })
                .catch((e) => {
                    this.error = `加载可视化 '${this.args.visualization_id}' 失败。`;
                    this.loading = false;
                });
        },
    },
};
</script>
