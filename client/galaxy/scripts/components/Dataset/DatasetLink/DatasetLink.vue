<template>
    <div>
        <a :href="pathDestination.fileLink" title="test" target="_blank">{{ linkLabel }}</a>
    </div>
</template>

<script>
import { getAppRoot } from "onload/loadConfig";
import { Services } from "components/Dataset/services";
import { getPathDestination } from "components/Dataset/compositeDatasetUtils";

export default {
    props: {
        history_dataset_id: {
            type: String,
            required: true,
        },
        path: {
            type: String,
        },
        label: {
            type: String,
        },
    },
    created() {
        this.services = new Services({ root: getAppRoot() });
        this.pathDestination = {};
        if (this.path && this.path !== "undefined") {
            // download individual file from composite dataset
            getPathDestination(this.history_dataset_id, this.path).then((pathDestination) => {
                this.pathDestination = pathDestination;
            });
        } else {
            // download whole dataset
            this.services.getCompositeDatasetInfo(this.history_dataset_id).then((response) => {
                this.pathDestination = { fileLink: `${response.download_url}?to_ext=${response.file_ext}` };
            });
        }
    },
    data() {
        return {
            pathDestination: undefined,
        };
    },
    computed: {
        linkLabel() {
            // if sub-directory, we could potentially implement subdir compression
            if (this.pathDestination.isDirectory) return `Path: ${this.path} is a directory!`;

            if (!this.pathDestination.fileLink) return `Path: ${this.path} was not found!`;

            if (this.label !== undefined && this.label !== "undefined") {
                return this.label;
            } else {
                return `${
                    this.pathDestination.datasetRootDir && this.path
                        ? `DATASET: ${this.pathDestination.datasetRootDir} FILEPATH: ${this.path}`
                        : `${this.history_dataset_id}`
                } `;
            }
        },
        isImage() {
            return (this.image && this.image === true) || this.image === "true";
        },
    },
};
</script>
