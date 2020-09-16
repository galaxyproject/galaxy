<template>
    <div>
        <h3 v-if="includeTitle">Dataset Storage</h3>
        <loading-span v-if="storageInfo == null"> </loading-span>
        <div v-else>
            <p v-if="storageInfo.name">
                This data is stored in a Galaxy ObjectStore named <b>{{ storageInfo.name }}</b
                >.
            </p>
            <p v-if="storageInfo.object_store_id">
                This data is stored in a Galaxy ObjectStore with id <b>{{ storageInfo.object_store_id }}</b
                >.
            </p>
            <div v-html="descriptionRendered"></div>
        </div>
    </div>
</template>

<script>
import axios from "axios";
import { getAppRoot } from "onload/loadConfig";
import LoadingSpan from "components/LoadingSpan";
import MarkdownIt from "markdown-it";

const md = MarkdownIt();

export default {
    components: {
        LoadingSpan,
    },
    props: {
        datasetId: {
            type: String,
        },
        datasetType: {
            type: String,
            default: "hda",
        },
        includeTitle: {
            type: Boolean,
            default: true,
        },
    },
    data() {
        return {
            storageInfo: null,
            descriptionRendered: null,
        };
    },
    created() {
        const datasetId = this.datasetId;
        const datasetType = this.datasetType;
        axios
            .get(`${getAppRoot()}api/datasets/${datasetId}/storage?hda_ldda=${datasetType}`)
            .then(this.handleResponse)
            .catch(this.handleError);
    },
    methods: {
        handleResponse(response) {
            console.log(response);
            this.storageInfo = response.data;
            this.descriptionRendered = md.render(this.storageInfo.description);
        },
        handleError(err) {
            console.log(err);
        },
    },
};
</script>
