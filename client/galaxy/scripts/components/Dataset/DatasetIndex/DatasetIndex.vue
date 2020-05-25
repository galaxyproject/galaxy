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
            <b v-if="this.datasetRootDir">{{ path }}</b> {{ errorMessage }}
        </div>
    </div>
</template>

<script>
import { getAppRoot } from "onload/loadConfig";
import { Services } from "components/Dataset/services";

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
        this.root = getAppRoot();
        this.services = new Services({ root: this.root });
        this.services.getCompositeDatasetContentFiles(this.history_dataset_id).then((datasetContent) => {
            if (datasetContent[0].class === "Directory") this.datasetRootDir = datasetContent[0].path;
            else {
                this.errorMessage = `Dataset is not composite!`;
                return;
            }

            if (this.path === undefined || this.path === "undefined") {
                this.directoryContent = this.removeParentDirectory(datasetContent, this.datasetRootDir);
                return;
            }

            const filepath = `${this.datasetRootDir}/${this.path}`;

            const datasetEntry = datasetContent.find((datasetEntry) => {
                return filepath === datasetEntry.path;
            });

            if (datasetEntry) {
                if (datasetEntry.class === "Directory") {
                    this.directoryContent = this.removeParentDirectory(datasetContent, filepath);
                } else this.errorMessage = ` is not a directory!`;
            } else {
                this.errorMessage = ` is not found!`;
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
