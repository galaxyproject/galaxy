<template>
    <div>
        <a v-if="!directoryContent" :href="fileLink" title="test" target="_blank">{{linkLabel}}</a>
        <div v-else="directoryContent" class="directory-content">
            <div v-html="directoryContent"></div>
        </div>
    </div>
</template>

<style lang="scss" scoped>

    div.directory-content {
        text-align: center;

        ::v-deep table {
            border: 1px solid black;
            margin-left: auto;
            margin-right: auto;
        }
    }

</style>

<script>

    import {getAppRoot} from "onload/loadConfig";
    import {Services} from "./services";

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
                this.root = getAppRoot();
                this.services = new Services({root: this.root});
                this.services.getCompositeDatasetContentFiles(this.history_dataset_id).then((datasetContent) => {

                    if (datasetContent[0].class === "Directory")
                        this.datasetRootDir = datasetContent[0].path
                    else return


                    const datasetEntry = datasetContent.find((datasetEntry) => {
                        return `${this.datasetRootDir}/${this.path}` === datasetEntry.path
                    })

                    if (datasetEntry) {
                        this.fileLink = this.getCompositeDatasetLink(this.history_dataset_id, datasetEntry.path)
                        if (datasetEntry.class === "Directory")
                            this.services.getCompositeDatasetDirectory(this.fileLink).then(response => {
                                this.directoryContent = response
                            })
                    }
                })
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
                if (!this.fileLink)
                    return `Path: ${this.path} was not found!`


                if (this.label !== undefined && this.label !== "undefined") {
                    return this.label
                } else {
                    return `DATASET: ${this.datasetRootDir} FILE: ${this.path}`
                }
            }
        },
        methods: {
            getCompositeDatasetLink(history_dataset_id, path) {
                return `${this.root}api/histories/${this.history_dataset_id}/contents/${history_dataset_id}/display?filename=${path}`
            }
        }
    };
</script>
