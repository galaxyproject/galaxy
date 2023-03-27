<template>
    <div>
        <h2 v-if="includeTitle" class="h-md">Dataset Storage</h2>
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
            <describe-object-store what="This dataset is stored in" :storage-info="storageInfo" />
        </div>
    </div>
</template>

<script>
import axios from "axios";
import { getAppRoot } from "onload/loadConfig";
import { errorMessageAsString } from "utils/simple-error";
import DescribeObjectStore from "components/ObjectStore/DescribeObjectStore";
import LoadingSpan from "components/LoadingSpan";

export default {
    components: {
        DescribeObjectStore,
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
            this.storageInfo = storageInfo;
        },
    },
};
</script>
