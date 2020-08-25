<template>
    <span>
        <b-dropdown no-caret right role="button" variant="link" title="Insert Datasets" v-b-tooltip.hover.bottom>
            <template v-slot:button-content>
                <font-awesome-icon icon="file" />
            </template>
            <b-dropdown-item href="#" @click="onDropdownClick('history_dataset_display')">
                <font-awesome-icon class="mr-1" icon="file" fixed-width />
                History Dataset Display
            </b-dropdown-item>
            <b-dropdown-item href="#" @click="onDropdownClick('history_dataset_collection_display')">
                <font-awesome-icon class="mr-1" icon="folder" fixed-width />
                History Dataset Collection Display
            </b-dropdown-item>
            <b-dropdown-item href="#" @click="onDropdownClick('history_dataset_as_image')">
                <font-awesome-icon class="mr-1" icon="image" fixed-width />
                History Dataset As Image
            </b-dropdown-item>
            <b-dropdown-item href="#" @click="onDropdownClick('history_dataset_index')">
                <font-awesome-icon class="mr-1" icon="list-alt" fixed-width />
                History Dataset Index
            </b-dropdown-item>
            <b-dropdown-item href="#" @click="onDropdownClick('history_dataset_embedded')">
                <font-awesome-icon class="mr-1" icon="clone" fixed-width />
                History Dataset Embedded
            </b-dropdown-item>
            <b-dropdown-item href="#" @click="onDropdownClick('history_dataset_type')">
                <font-awesome-icon class="mr-1" icon="flag" fixed-width />
                History Dataset Type
            </b-dropdown-item>
            <b-dropdown-item href="#" @click="onDropdownClick('history_dataset_link')">
                <font-awesome-icon class="mr-1" icon="link" fixed-width />
                History Dataset Link
            </b-dropdown-item>
            <b-dropdown-item href="#" @click="onDropdownClick('history_dataset_info')">
                <font-awesome-icon class="mr-1" icon="info" fixed-width />
                History Dataset Information
            </b-dropdown-item>
            <b-dropdown-item href="#" @click="onDropdownClick('history_dataset_name')">
                <font-awesome-icon class="mr-1" icon="signature" fixed-width />
                History Dataset Name
            </b-dropdown-item>
            <b-dropdown-item href="#" @click="onDropdownClick('history_dataset_peek')">
                <font-awesome-icon class="mr-1" icon="search-location" fixed-width />
                History Dataset Peek
            </b-dropdown-item>
        </b-dropdown>
        <b-dropdown no-caret right role="button" variant="link" title="Insert Jobs" v-b-tooltip.hover.bottom>
            <template v-slot:button-content>
                <font-awesome-icon icon="wrench" />
            </template>
            <b-dropdown-item href="#" @click="onDropdownClick('job_metrics')">
                <font-awesome-icon class="mr-1" icon="tachometer-alt" fixed-width />
                Job Metrics
            </b-dropdown-item>
            <b-dropdown-item href="#" @click="onDropdownClick('job_parameters')">
                <font-awesome-icon class="mr-1" icon="tasks" fixed-width />
                Job Parameters
            </b-dropdown-item>
            <b-dropdown-item href="#" @click="onDropdownClick('tool_stdout')">
                <font-awesome-icon class="mr-1" icon="quote-right" fixed-width />
                Tool Standard Output
            </b-dropdown-item>
            <b-dropdown-item href="#" @click="onDropdownClick('tool_stderr')">
                <font-awesome-icon class="mr-1" icon="bug" fixed-width />
                Tool Error Output
            </b-dropdown-item>
        </b-dropdown>
        <b-dropdown no-caret right role="button" variant="link" title="Insert Workflows" v-b-tooltip.hover.bottom>
            <template v-slot:button-content>
                <font-awesome-icon icon="sitemap" rotation="270" />
            </template>
            <b-dropdown-item href="#" @click="onDropdownClick('invocation_inputs')">
                <font-awesome-icon class="mr-1" icon="arrow-right" fixed-width />
                Invocation Inputs
            </b-dropdown-item>
            <b-dropdown-item href="#" @click="onDropdownClick('invocation_outputs')">
                <font-awesome-icon class="mr-1" icon="arrow-left" fixed-width />
                Invocation Outputs
            </b-dropdown-item>
            <b-dropdown-item href="#" @click="onDropdownClick('invocation_time')">
                <font-awesome-icon class="mr-1" icon="clock" fixed-width />
                Invocation Time
            </b-dropdown-item>
            <b-dropdown-item href="#" @click="onDropdownClick('workflow_display')">
                <font-awesome-icon class="mr-1" icon="sitemap" fixed-width rotation="270" />
                Workflow Display
            </b-dropdown-item>
        </b-dropdown>
        <b-dropdown no-caret right role="button" variant="link" title="Insert Others" v-b-tooltip.hover.bottom>
            <template v-slot:button-content>
                <font-awesome-icon icon="tools" />
            </template>
            <b-dropdown-item href="#" @click="onDropdownClick('generate_galaxy_version')">
                <font-awesome-icon class="mr-1" icon="certificate" fixed-width />
                Galaxy Version
            </b-dropdown-item>
            <b-dropdown-item href="#" @click="onDropdownClick('generate_time')">
                <font-awesome-icon class="mr-1" fixed-width rotation="270" icon="clock" />
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
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import {
    faClock,
    faCertificate,
    faSitemap,
    faInfo,
    faFile,
    faFolder,
    faLink,
    faSignature,
    faImage,
    faWrench,
    faTools,
    faBug,
    faArrowRight,
    faQuoteRight,
    faArrowLeft,
    faTachometerAlt,
    faTasks,
    faSearchLocation,
    faListAlt,
    faClone,
    faFlag,
} from "@fortawesome/free-solid-svg-icons";

import MarkdownDialog from "./MarkdownDialog";

Vue.use(BootstrapVue);

library.add(
    faClock,
    faSitemap,
    faFile,
    faFolder,
    faLink,
    faInfo,
    faSignature,
    faImage,
    faWrench,
    faTools,
    faBug,
    faArrowRight,
    faArrowLeft,
    faQuoteRight,
    faTachometerAlt,
    faTasks,
    faCertificate,
    faSearchLocation,
    faListAlt,
    faClone,
    faFlag,
);

export default {
    components: {
        FontAwesomeIcon,
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
