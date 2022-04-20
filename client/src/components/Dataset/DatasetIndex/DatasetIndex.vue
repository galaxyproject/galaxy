<template>
    <div>
        <b-table
            v-if="directoryContent && !errorMessage"
            thead-class="hidden_header"
            striped
            hover
            :fields="fields"
            :items="directoryContent">
        </b-table>
        <div v-if="errorMessage">
            <b v-if="path">{{ path }}</b> {{ errorMessage }}
        </div>
    </div>
</template>

<script>
import { mapCacheActions } from "vuex-cache";

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
    created() {
        this.fetchPathDestination({ history_dataset_id: this.history_dataset_id, path: this.path }).then(() => {
            const pathDestination = this.$store.getters.pathDestination(this.history_dataset_id, this.path);
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
                this.directoryContent = pathDestination.datasetContent;
            } else {
                this.errorMessage = `is not found!`;
            }
        });
    },
    methods: {
        ...mapCacheActions(["fetchPathDestination"]),

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
