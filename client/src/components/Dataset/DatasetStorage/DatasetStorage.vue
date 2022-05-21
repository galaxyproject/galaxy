<template>
    <div>
        <h3 v-if="includeTitle">Dataset Storage</h3>
        <div v-if="errorMessage" class="error">{{ errorMessage }}</div>
        <loading-span v-else-if="storageInfo == null"> </loading-span>
        <div v-else>
            <p>
                This dataset is stored in
                <span v-if="storageInfo.name" class="display-os-by-name">
                    a Galaxy object store named <b>{{ storageInfo.name }}</b>
                </span>
                <span v-else-if="storageInfo.object_store_id" class="display-os-by-id">
                    a Galaxy object store with id <b>{{ storageInfo.object_store_id }}</b>
                </span>
                <span v-else class="display-os-default"> the default configured Galaxy object store </span>.
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
import { errorMessageAsString } from "utils/simple-error";

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
            errorMessage: null,
        };
    },
    created() {
        const datasetId = this.datasetId;
        const datasetType = this.datasetType;
        axios
            .get(`${getAppRoot()}api/datasets/${datasetId}/storage`, { hda_ldda: datasetType })
            .then(this.handleResponse)
            .catch((errorMessage) => {
                this.errorMessage = errorMessageAsString(errorMessage);
            });
    },
    methods: {
        handleResponse(response) {
            const storageInfo = response.data;
            const description = storageInfo.description;
            this.storageInfo = storageInfo;
            if (description) {
                this.descriptionRendered = MarkdownIt({ html: true }).render(storageInfo.description);
            } else {
                this.descriptionRendered = null;
            }
        },
    },
};
</script>
