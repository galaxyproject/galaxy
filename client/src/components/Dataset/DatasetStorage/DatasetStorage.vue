<template>
    <div>
        <h3 v-if="includeTitle">Dataset Storage</h3>
        <div v-if="errorMessage" class="error">{{ errorMessage }}</div>
        <loading-span v-else-if="storageInfo == null"> </loading-span>
        <div v-else-if="discarded">
            <p>This dataset has been discarded and its files are not available to Galaxy.</p>
        </div>
        <div v-else-if="deferred">
            <p>
                This dataset is remote and deferred. The dataset's files are not available to Galaxy.
                <span v-if="sourceUri">
                    This dataset will be downloaded from <b class="deferred-dataset-source-uri">{{ sourceUri }}</b> when
                    jobs use this dataset.
                </span>
            </p>
        </div>
        <div v-else>
            <p>
                This dataset is stored in
                <span class="display-os-by-name" v-if="storageInfo.name">
                    a Galaxy <object-store-restriction-span :is-private="isPrivate" /> object store named
                    <b>{{ storageInfo.name }}</b>
                </span>
                <span class="display-os-by-id" v-else-if="storageInfo.object_store_id">
                    a Galaxy <object-store-restriction-span :is-private="isPrivate" /> object store with id
                    <b>{{ storageInfo.object_store_id }}</b>
                </span>
                <span class="display-os-default" v-else>
                    the default configured Galaxy <object-store-restriction-span :is-private="isPrivate" /> object store </span
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
import { errorMessageAsString } from "utils/simple-error";
import ObjectStoreRestrictionSpan from "./ObjectStoreRestrictionSpan";

export default {
    components: {
        LoadingSpan,
        ObjectStoreRestrictionSpan,
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
    computed: {
        discarded() {
            return this.storageInfo.dataset_state == "discarded";
        },
        deferred() {
            return this.storageInfo.dataset_state == "deferred";
        },
        sourceUri() {
            const sources = this.storageInfo.sources;
            if (!sources) {
                return null;
            }
            const rootSources = sources.filter((source) => !source.extra_files_path);
            if (rootSources.length == 0) {
                return null;
            }
            return rootSources[0].source_uri;
        },
        isPrivate() {
            return this.storageInfo.private;
        },
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
