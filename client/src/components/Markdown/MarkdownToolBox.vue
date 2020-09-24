<template>
    <div class="unified-panel">
        <div class="unified-panel-header" unselectable="on">
            <div class="unified-panel-header-inner">
                <div class="panel-header-text">Insert Objects</div>
            </div>
        </div>
        <div class="unified-panel-body">
            <div class="toolMenuContainer">
                <tool-section :category="historySection" @onClick="onClick" :expanded="true" />
                <tool-section :category="jobSection" @onClick="onClick" :expanded="true" />
                <tool-section
                    v-if="isWorkflow"
                    :category="workflowInEditorSection"
                    @onClick="onClick"
                    :expanded="true"
                />
                <tool-section v-else :category="workflowSection" @onClick="onClick" :expanded="true" />
                <tool-section :category="otherSection" @onClick="onClick" :expanded="true" />
                <tool-section v-if="!isWorkflow" :category="visualizationSection" @onClick="onClick" />
            </div>
        </div>
        <MarkdownDialog
            v-if="selectedShow"
            :argument-type="selectedType"
            :argument-name="selectedArgumentName"
            :labels="selectedLabels"
            :use-labels="isWorkflow"
            @onInsert="onInsert"
            @onCancel="onCancel"
        />
    </div>
</template>

<script>
import Vue from "vue";
import axios from "axios";
import BootstrapVue from "bootstrap-vue";
import ToolSection from "components/Panels/Common/ToolSection";
import MarkdownDialog from "./MarkdownDialog";
import { showMarkdownHelp } from "./markdownHelp";
import { getAppRoot } from "onload/loadConfig";

Vue.use(BootstrapVue);

export default {
    components: {
        MarkdownDialog,
        ToolSection,
    },
    props: {
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
            historySection: {
                title: "History",
                name: "history",
                elems: [
                    {
                        id: "history_dataset_display",
                        name: "Dataset",
                        emitter: "onHistoryId",
                    },
                    {
                        id: "history_collection_display",
                        name: "Collection",
                        emitter: "onHistoryCollectionId",
                    },
                    {
                        id: "history_dataset_as_image",
                        name: "Image",
                        emitter: "onHistoryId",
                    },
                    {
                        id: "history_dataset_index",
                        name: "Dataset Index",
                        emitter: "onHistoryId",
                    },
                    {
                        id: "history_dataset_embedded",
                        name: "Embedded Dataset",
                        emitter: "onHistoryId",
                    },
                    {
                        id: "history_dataset_type",
                        name: "Dataset Type",
                        emitter: "onHistoryId",
                    },
                    {
                        id: "history_dataset_link",
                        name: "Link to Dataset",
                        emitter: "onHistoryId",
                    },
                    {
                        id: "history_dataset_name",
                        name: "Name of Dataset",
                        emitter: "onHistoryId",
                    },
                    {
                        id: "history_dataset_peek",
                        name: "Peek into Dataset",
                        emitter: "onHistoryId",
                    },
                    {
                        id: "history_dataset_info",
                        name: "Dataset Details",
                        emitter: "onHistoryId",
                    },
                ],
            },
            jobSection: {
                title: "Jobs",
                name: "jobs",
                elems: [
                    {
                        id: "job_metrics",
                        name: "Job Metrics",
                        description: "as table",
                        emitter: "onJobId",
                    },
                    {
                        id: "job_parameters",
                        name: "Job Parameters",
                        description: "as table",
                        emitter: "onJobId",
                    },
                    {
                        id: "tool_stdout",
                        name: "Tool Output",
                        description: "of job run",
                        emitter: "onJobId",
                    },
                    {
                        id: "tool_stderr",
                        name: "Tool Error",
                        description: "of job run",
                        emitter: "onJobId",
                    },
                ],
            },
            workflowSection: {
                title: "Workflow",
                name: "workflow",
                elems: [
                    {
                        id: "invocation_time",
                        name: "Invocation Time",
                        emitter: "onInvocationId",
                    },
                    {
                        id: "workflow_display",
                        name: "Workflow Display",
                        emitter: "onWorkflowId",
                    },
                ],
            },
            workflowInEditorSection: {
                title: "Workflow",
                name: "workflow",
                elems: [
                    {
                        id: "invocation_inputs",
                        name: "Invocation Inputs",
                    },
                    {
                        id: "invocation_outputs",
                        name: "Invocation Output",
                    },
                    {
                        id: "invocation_time",
                        name: "Time a Workflow",
                        description: "was invoked",
                    },
                    {
                        id: "workflow_display",
                        name: "Current Workflow",
                        description: "containing all steps",
                    },
                ],
            },
            otherSection: {
                title: "Miscellaneous",
                name: "others",
                elems: [
                    {
                        id: "generate_galaxy_version",
                        name: "Galaxy Version",
                        description: "as text",
                    },
                    {
                        id: "generate_time",
                        name: "Current Time",
                        description: "as text",
                    },
                ],
            },
            visualizationSection: {
                title: "Visualizations",
                name: "visualizations",
                elems: [],
            },
        };
    },
    computed: {
        isWorkflow() {
            return !!this.nodes;
        },
    },
    created() {
        this.getVisualizations();
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
        onClick(item) {
            switch (item.emitter) {
                case "onHistoryId":
                    this.onHistoryId(item.id);
                    break;
                case "onHistoryCollectionId":
                    this.onHistoryCollectionId(item.id);
                    break;
                case "onJobId":
                    this.onJobId(item.id);
                    break;
                case "onWorkflowId":
                    this.onWorkflowId(item.id);
                    break;
                case "onInvocationId":
                    this.onInvocationId(item.id);
                    break;
                default:
                    this.onNoParameter(item.id);
            }
        },
        onInsert(markdownBlock) {
            this.$emit("onInsert", markdownBlock);
            this.selectedShow = false;
        },
        onCancel() {
            this.selectedShow = false;
        },
        onNoParameter(argumentName) {
            this.onInsert(`${argumentName}()`);
        },
        onHistoryId(argumentName) {
            this.selectedArgumentName = argumentName;
            this.selectedType = "history_dataset_id";
            this.selectedLabels = this.getOutputs();
            this.selectedShow = true;
        },
        onHistoryCollectionId(argumentName) {
            this.selectedArgumentName = argumentName;
            this.selectedType = "history_dataset_collection_id";
            this.selectedLabels = this.getOutputs();
            this.selectedShow = true;
        },
        onWorkflowId(argumentName) {
            this.selectedArgumentName = argumentName;
            this.selectedType = "workflow_id";
            this.selectedShow = true;
        },
        onJobId(argumentName) {
            this.selectedArgumentName = argumentName;
            this.selectedType = "job_id";
            this.selectedLabels = this.getSteps();
            this.selectedShow = true;
        },
        onInvocationId(argumentName) {
            this.selectedArgumentName = argumentName;
            this.selectedType = "invocation_id";
            this.selectedLabels = this.getSteps();
            this.selectedShow = true;
        },
        onHelp() {
            showMarkdownHelp();
        },
        async getVisualizations() {
            axios
                .get(`${getAppRoot()}api/plugins`)
                .then((response) => {
                    this.visualizationSection.elems = response.data.map((x) => {
                        return {
                            id: `visualization(id=${x.name})`,
                            name: x.html,
                            description: x.description,
                            logo: x.logo ? `${getAppRoot()}${x.logo}` : null,
                            emitter: "onHistoryId",
                        };
                    });
                })
                .catch((e) => {
                    this.error = this._errorMessage(e);
                });
        },
    },
};
</script>
