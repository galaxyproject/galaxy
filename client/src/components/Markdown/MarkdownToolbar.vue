<template>
    <span>
        <b-dropdown no-caret right role="button" variant="link" title="Insert Datasets" v-b-tooltip.hover.bottom>
            <template v-slot:button-content>
                <span class="fa fa-file" />
            </template>
            <b-dropdown-item href="#" @click="onDropdownClick('history_dataset_display')">
                <span class="fa fa-fw mr-1 fa-file-o" />
                History Dataset Display
            </b-dropdown-item>
            <b-dropdown-item href="#" @click="onDropdownClick('history_dataset_collection_display')">
                <span class="fa fa-fw mr-1 fa-folder-o" />
                History Dataset Collection Display
            </b-dropdown-item>
            <b-dropdown-item href="#" @click="onDropdownClick('history_dataset_as_image')">
                <span class="fa fa-fw mr-1 fa-image" />
                History Dataset As Image
            </b-dropdown-item>
            <b-dropdown-item href="#" @click="onDropdownClick('history_dataset_index')">
                <span class="fa fa-fw mr-1" />
                History Dataset Index
            </b-dropdown-item>
            <b-dropdown-item href="#" @click="onDropdownClick('history_dataset_embedded')">
                <span class="fa fa-fw mr-1" />
                History Dataset Embedded
            </b-dropdown-item>
            <b-dropdown-item href="#" @click="onDropdownClick('history_dataset_type')">
                <span class="fa fa-fw mr-1" />
                History Dataset Type
            </b-dropdown-item>
            <b-dropdown-item href="#" @click="onDropdownClick('history_dataset_link')">
                <span class="fa fa-fw mr-1 fa-link" />
                History Dataset Link
            </b-dropdown-item>
            <b-dropdown-item href="#" @click="onDropdownClick('history_dataset_info')">
                <span class="fa fa-fw mr-1 fa-info" />
                History Dataset Information
            </b-dropdown-item>
            <b-dropdown-item href="#" @click="onDropdownClick('history_dataset_name')">
                <span class="fa fa-fw mr-1 fa-signature" />
                History Dataset Name
            </b-dropdown-item>
            <b-dropdown-item href="#" @click="onDropdownClick('history_dataset_peek')">
                <span class="fa fa-fw mr-1" />
                History Dataset Peek
            </b-dropdown-item>
        </b-dropdown>
        <b-dropdown no-caret right role="button" variant="link" title="Insert Jobs" v-b-tooltip.hover.bottom>
            <template v-slot:button-content>
                <span class="fa fa-wrench" />
            </template>
            <b-dropdown-item href="#" @click="onDropdownClick('job_metrics')">
                <span class="fa fa-fw mr-1 fa-tachometer-alt" />
                Job Metrics
            </b-dropdown-item>
            <b-dropdown-item href="#" @click="onDropdownClick('job_parameters')">
                <span class="fa fa-fw mr-1 fa-tasks" />
                Job Parameters
            </b-dropdown-item>
            <b-dropdown-item href="#" @click="onDropdownClick('tool_stdout')">
                <span class="fa fa-fw mr-1 fa-quote-right" />
                Tool Standard Output
            </b-dropdown-item>
            <b-dropdown-item href="#" @click="onDropdownClick('tool_stderr')">
                <span class="fa fa-fw mr-1 fa-bug" />
                Tool Error Output
            </b-dropdown-item>
        </b-dropdown>
        <b-dropdown no-caret right role="button" variant="link" title="Insert Workflows" v-b-tooltip.hover.bottom>
            <template v-slot:button-content>
                <span class="fa fa-sitemap fa-rotate-270" />
            </template>
            <b-dropdown-item href="#" @click="onDropdownClick('invocation_inputs')">
                <span class="fa fa-fw mr-1 fa-arrow-right" />
                Invocation Inputs
            </b-dropdown-item>
            <b-dropdown-item href="#" @click="onDropdownClick('invocation_outputs')">
                <span class="fa fa-fw mr-1 fa-arrow-left" />
                Invocation Outputs
            </b-dropdown-item>
            <b-dropdown-item href="#" @click="onDropdownClick('invocation_time')">
                <span class="fa fa-fw mr-1 fa-clock" />
                Invocation Time
            </b-dropdown-item>
            <b-dropdown-item href="#" @click="onDropdownClick('workflow_display')">
                <span class="fa fa-fw mr-1 fa-sitemap fa-rotate-270" />
                Workflow Display
            </b-dropdown-item>
        </b-dropdown>
        <b-dropdown no-caret right role="button" variant="link" title="Insert Others" v-b-tooltip.hover.bottom>
            <template v-slot:button-content>
                <span class="fa fa-tools" />
            </template>
            <b-dropdown-item href="#" @click="onDropdownClick('generate_galaxy_version')">
                <span class="fa fa-fw mr-1" />
                Galaxy Version
            </b-dropdown-item>
            <b-dropdown-item href="#" @click="onDropdownClick('generate_time')">
                <span class="fa fa-fw mr-1" />
                Time Stamp
            </b-dropdown-item>
        </b-dropdown>
        <MarkdownDialog
            v-if="selectedShow"
            :argument-type="selectedType"
            :argument-name="selectedArgumentName"
            :labels="selectedLabels"
            :use-labels="useLabels"
            @onInsert="onInsert"
            @onCancel="onCancel"
        />
    </span>
</template>

<script>
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import MarkdownDialog from "./MarkdownDialog";

Vue.use(BootstrapVue);

export default {
    components: {
        MarkdownDialog,
    },
    props: {
        validArguments: {
            type: Object,
            default: null,
        },
        nodes: {
            type: Object,
            default: null,
        },
    },
    data() {
        return {
            selectedArgumentName: null,
            selectedType: null,
            selectedLabels: null,
            selectedShow: false,
        };
    },
    computed: {
        useLabels() {
            return !!this.nodes;
        },
    },
    methods: {
        getSteps() {
            const steps = [];
            this.nodes &&
                Object.values(this.nodes).forEach((node) => {
                    if (node.label) {
                        steps.push(node.label);
                    }
                });
            return steps;
        },
        getOutputs() {
            const outputLabels = [];
            this.nodes &&
                Object.values(this.nodes).forEach((node) => {
                    node.outputs.forEach((output) => {
                        if (output.activeLabel) {
                            outputLabels.push(output.activeLabel);
                        }
                    });
                });
            return outputLabels;
        },
        getArgumentTitle(argumentName) {
            return (
                argumentName[0].toUpperCase() +
                argumentName.substr(1).replace(/_([a-z])/g, (g) => {
                    return ` ${g[1].toUpperCase()}`;
                })
            );
        },
        onInsert(markdownBlock) {
            this.$emit("onInsert", markdownBlock);
            this.selectedShow = false;
        },
        onCancel() {
            this.selectedShow = false;
        },
        onDropdownClick(argumentName) {
            this.selectedArgumentName = argumentName;
            const arg = this.validArguments[argumentName];
            if (arg.length == 0) {
                this.$emit("onInsert", `${argumentName}()`);
            } else if (arg.includes("workflow_id")) {
                this.selectedType = "workflow_id";
                this.selectedShow = true;
            } else if (arg.includes("job_id")) {
                this.selectedType = "job_id";
                this.selectedLabels = this.getSteps();
                this.selectedShow = true;
            } else if (arg.includes("invocation_id")) {
                this.selectedType = "invocation_id";
                this.selectedLabels = this.getSteps();
                this.selectedShow = true;
            } else if (arg.includes("history_dataset_id")) {
                this.selectedType = "history_dataset_id";
                this.selectedLabels = this.getOutputs();
                this.selectedShow = true;
            } else if (arg.includes("history_dataset_collection_id")) {
                this.selectedType = "history_dataset_collection_id";
                this.selectedLabels = this.getOutputs();
                this.selectedShow = true;
            } else {
                this.$emit("onInsert", `${argumentName}(${arg.join(", ")}=<ENTER A VALUE>)`);
            }
        },
    },
};
</script>
