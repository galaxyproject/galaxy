<template>
    <div>
        <a v-if="!directoryContent && !isImage" :href="fileLink" title="test" target="_blank">{{ linkLabel }}</a>
        <div v-if="directoryContent && !isImage" class="directory-content">
            <div v-html="directoryContent"></div>
        </div>
        <img v-if="isImage" :src="fileLink" />
    </div>
</template>

<style lang="scss" scoped>
div.directory-content {
    text-align: center;

    /*
        Deep selectors on Dynamically Generated Content
        https://vue-loader.vuejs.org/guide/scoped-css.html#child-component-root-elements
        */

    ::v-deep table {
        border: 1px solid black;
        margin-left: auto;
        margin-right: auto;
    }
}
</style>

<script>
import { getAppRoot } from "onload/loadConfig";
import { Services } from "./services";

export default {
    props: {
        history_dataset_id: {
            type: String,
            required: true,
        },
        path: {
            type: String,
        },
        image: {},
        label: {
            type: String,
        },
    },
    created() {
        this.root = getAppRoot();
        this.services = new Services({ root: this.root });

        if (this.path && this.path !== "undefined") {
            // download individual file from composite dataset
            this.services.getCompositeDatasetContentFiles(this.history_dataset_id).then((datasetContent) => {
                if (datasetContent[0].class === "Directory") this.datasetRootDir = datasetContent[0].path;
                else return;

                const datasetEntry = datasetContent.find((datasetEntry) => {
                    return `${this.datasetRootDir}/${this.path}` === datasetEntry.path;
                });

                if (datasetEntry) {
                    this.fileLink = this.getCompositeDatasetLink(this.history_dataset_id, datasetEntry.path);
                    if (datasetEntry.class === "Directory")
                        this.services.getCompositeDatasetDirectory(this.fileLink).then((response) => {
                            this.directoryContent = response;
                        });
                }
            });
        } else {
            // download whole dataset
            this.services.getCompositeDatasetInfo(this.history_dataset_id).then((response) => {
                this.fileLink = `${response.download_url}?to_ext=${response.file_ext}`;
            });
        }
    },
    data() {
        return {
            fileLink: false,
            directoryContent: false,
            datasetRootDir: "",
        };
    },
    computed: {
        linkLabel() {
            if (!this.fileLink) return `Path: ${this.path} was not found!`;

            if (this.label !== undefined && this.label !== "undefined") {
                return this.label;
            } else {
                return `${
                    this.datasetRootDir && this.path
                        ? `DATASET: ${this.datasetRootDir} FILEPATH: ${this.path}`
                        : `${this.history_dataset_id}`
                } `;
            }
        },
        isImage() {
            return (this.image && this.image === true) || this.image === "true";
        },
    },
    methods: {
        getCompositeDatasetLink(history_dataset_id, path) {
            return `${this.root}api/histories/${this.history_dataset_id}/contents/${history_dataset_id}/display?filename=${path}`;
        },
    },
};
</script>
