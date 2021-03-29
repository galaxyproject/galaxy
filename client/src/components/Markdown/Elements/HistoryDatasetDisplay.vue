<template>
    <div class="w-50 p-2 float-left">
        <b-card body-class="p-0">
            <b-card-header v-if="!embedded">
                <span class="float-right">
                    <b-button
                        :href="downloadUrl"
                        variant="link"
                        size="sm"
                        role="button"
                        title="Download Dataset"
                        type="button"
                        class="py-0 px-1"
                        v-b-tooltip.hover
                    >
                        <span class="fa fa-download" />
                    </b-button>
                    <b-button
                        :href="importUrl"
                        role="button"
                        variant="link"
                        title="Import Dataset"
                        type="button"
                        class="py-0 px-1"
                        v-b-tooltip.hover
                    >
                        <span class="fa fa-file-import" />
                    </b-button>
                </span>
                <span>
                    <span>Dataset:</span>
                    <span class="font-weight-light">{{ datasetName }}</span>
                </span>
            </b-card-header>
            <b-card-body>
                <LoadingSpan v-if="loading" message="Loading Dataset" />
                <div v-else class="embedded-dataset content-height">
                    <pre v-if="itemContent.item_data">
                        <code class="text-normalwrap">{{ itemContent.item_data }}</code>
                    </pre>
                    <div v-else>No content found.</div>
                    <b-link v-if="itemContent.truncated" :href="itemContent.item_url"> Show More... </b-link>
                </div>
            </b-card-body>
        </b-card>
    </div>
</template>

<script>
import { getAppRoot } from "onload/loadConfig";
import LoadingSpan from "components/LoadingSpan";
import axios from "axios";
export default {
    components: {
        LoadingSpan,
    },
    props: {
        args: {
            type: Object,
            required: true,
        },
        datasets: {
            type: Object,
            required: true,
        },
        embedded: {
            type: Boolean,
            default: false,
        },
    },
    data() {
        return {
            itemContent: null,
            loading: true,
        };
    },
    created() {
        this.getContent().then((data) => {
            this.itemContent = data;
            this.loading = false;
        });
    },
    computed: {
        datasetName() {
            const dataset = this.datasets[this.args.history_dataset_id];
            return dataset && dataset.name;
        },
        downloadUrl() {
            return `${getAppRoot()}dataset/display?dataset_id=${this.args.history_dataset_id}`;
        },
        importUrl() {
            return `${getAppRoot()}dataset/imp?dataset_id=${this.args.history_dataset_id}`;
        },
        itemUrl() {
            return `${getAppRoot()}api/datasets/${this.args.history_dataset_id}/get_content_as_text`;
        },
    },
    methods: {
        async getContent() {
            try {
                const response = await axios.get(this.itemUrl);
                return response.data;
            } catch (e) {
                return `Failed to retrieve content. ${e}`;
            }
        },
    },
};
</script>
<style scoped>
.content-height {
    max-height: 15rem;
}
</style>
