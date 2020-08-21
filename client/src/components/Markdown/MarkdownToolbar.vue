<template>
    <span>
        <b-dropdown
            no-caret
            right
            id="workflow-options-button"
            role="button"
            title="Workflow Options"
            variant="link"
            v-b-tooltip.hover
        >
            <template v-slot:button-content>
                <span class="fa fa-cog" />
            </template>
            <b-dropdown-item href="#" @click="$emit('onSaveAs')"
                ><span class="fa fa-floppy-o mr-1" />Save As...</b-dropdown-item
            >
        </b-dropdown>
        <b-button
            title="Insert Dataset"
            variant="link"
            role="button"
            v-b-tooltip.hover.bottom
            @click="selectDataset"
        >
            <span class="fa fa-file" />
        </b-button>
    </span>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { showMarkdownHelp } from "./markdownHelp";

Vue.use(BootstrapVue);

import { dialog, datasetCollectionDialog, workflowDialog } from "utils/data";

export default {
    props: {
        validArguments: {
            type: Object,
            default: null,
        },
    },
    data() {
        return {
            categories: {},
        };
    },
    created() {
        console.log(this.validArguments);
    },
    methods: {
        selectDataset(galaxyCall) {
            dialog(
                (response) => {
                    const datasetId = response.id;
                    this.$emit("onInsert", `${galaxyCall}(history_dataset_id=${datasetId})`);
                },
                {
                    multiple: false,
                    format: null,
                    library: false, // TODO: support?
                }
            );
        },
        selectDatasetCollection(galaxyCall) {
            datasetCollectionDialog((response) => {
                this.$emit("onInsert", `${galaxyCall}(history_dataset_collection_id=${response.id})`);
            }, {});
        },
        selectWorkflow(galaxyCall) {
            workflowDialog((response) => {
                this.$emit("onInsert", `${galaxyCall}(workflow_display(workflow_id=${response.id})`);
            }, {});
        },
    },
};
</script>