<template>
    <div>
        <b-table
            thead-class="hidden_header"
            v-if="directoryContent && !errorMessage"
            striped
            hover
            :fields="fields"
            :items="directoryContent"
        >
        </b-table>
        <div v-if="errorMessage">
            <b v-if="path">{{ path }}</b> {{ errorMessage }}
        </div>
    </div>
</template>

<script>
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
    },
    created() {
        getPathDestination(this.history_dataset_id, this.path).then((pathDestination) => {
            if (!pathDestination) {
                this.errorMessage = `Dataset is not composite!`;
                return;
            }
            if (pathDestination.fileLink) {
                this.errorMessage = `is not a directory!`;
                return;
            }

            if (pathDestination.isDirectory) {
                this.directoryContent = this.removeParentDirectory(
                    pathDestination.datasetContent,
                    pathDestination.filepath
                );
            } else if (this.path === undefined || this.path === "undefined") {
                this.directoryContent = this.removeParentDirectory(
                    pathDestination.datasetContent,
                    pathDestination.datasetRootDir
                );
            } else {
                this.errorMessage = `is not found!`;
            }
        });
    },
    data() {
        return {
            directoryContent: false,
            fields: [
                {
                    key: "path",
                    sortable: true,
                },
                {
                    key: "class",
                    label: "Type",
                    sortable: true,
                },
            ],
            errorMessage: undefined,
        };
    },
    methods: {
        removeParentDirectory(datasetContent, filepath) {
            return datasetContent.filter((entry) => {
                if (entry.path.startsWith(`${filepath}/`)) {
                    entry.path = entry.path.replace(`${filepath}/`, "");
                    return entry;
                }
            });
        },
    },
};
</script>
