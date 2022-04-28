<template>
    <div class="unified-panel">
        <div class="unified-panel-header" unselectable="on">
            <div class="unified-panel-header-inner">
                <div class="panel-header-text">Insert Objects</div>
            </div>
        </div>
        <div class="unified-panel-body">
            <div class="toolMenuContainer">
                <b-alert v-if="error" variant="danger" class="my-2 mx-3 px-2 py-1" show>
                    {{ error }}
                </b-alert>
                <tool-section
                    v-if="isWorkflow"
                    :category="historyInEditorSection"
                    :expanded="true"
                    @onClick="onClick" />
                <tool-section v-else :category="historySection" :expanded="true" @onClick="onClick" />
                <tool-section :category="jobSection" :expanded="true" @onClick="onClick" />
                <tool-section
                    v-if="isWorkflow"
                    :category="workflowInEditorSection"
                    :expanded="true"
                    @onClick="onClick" />
                <tool-section v-else :category="workflowSection" :expanded="true" @onClick="onClick" />
                <tool-section :category="otherSection" :expanded="true" @onClick="onClick" />
                <tool-section
                    v-if="hasVisualizations"
                    :category="visualizationSection"
                    :expanded="true"
                    @onClick="onClick" />
            </div>
        </div>
        <MarkdownDialog
            v-if="selectedShow"
            :argument-type="selectedType"
            :argument-name="selectedArgumentName"
            :argument-payload="selectedPayload"
            :labels="selectedLabels"
            :use-labels="isWorkflow"
            @onInsert="onInsert"
            @onCancel="onCancel" />
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

const historySharedElements = [
    {
        id: "history_dataset_display",
        name: "Dataset",
        emitter: "onHistoryDatasetId",
    },
    {
        id: "history_dataset_collection_display",
        name: "Collection",
        emitter: "onHistoryCollectionId",
    },
    {
        id: "history_dataset_as_image",
        name: "Image",
        emitter: "onHistoryDatasetId",
    },
    {
        id: "history_dataset_index",
        name: "Dataset Index",
        emitter: "onHistoryDatasetId",
    },
    {
        id: "history_dataset_embedded",
        name: "Embedded Dataset",
        emitter: "onHistoryDatasetId",
    },
    {
        id: "history_dataset_type",
        name: "Dataset Type",
        emitter: "onHistoryDatasetId",
    },
    {
        id: "history_dataset_link",
        name: "Link to Dataset",
        emitter: "onHistoryDatasetId",
    },
    {
        id: "history_dataset_name",
        name: "Name of Dataset",
        emitter: "onHistoryDatasetId",
    },
    {
        id: "history_dataset_peek",
        name: "Peek into Dataset",
        emitter: "onHistoryDatasetId",
    },
    {
        id: "history_dataset_info",
        name: "Dataset Details",
        emitter: "onHistoryDatasetId",
    },
];

export default {
    components: {
        MarkdownDialog,
        ToolSection,
    },
    props: {
        getManager: {
            type: Function,
            default: null,
        },
    },
    data() {
        return {
            selectedArgumentName: null,
            selectedType: null,
            selectedLabels: null,
            selectedShow: false,
            selectedPayload: null,
            visualizationIndex: {},
            error: null,
            historySection: {
                title: "History",
                name: "history",
                elems: [
                    ...historySharedElements,
                    {
                        id: "history_link",
                        name: "Link to Import",
                        emitter: "onHistoryId",
                    },
                ],
            },
            historyInEditorSection: {
                title: "History",
                name: "history",
                elems: [
                    ...historySharedElements,
                    {
                        id: "history_link",
                        name: "Link to Import",
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
        hasVisualizations() {
            return this.visualizationSection.elems.length > 0;
        },
        nodes() {
            return this.getManager && this.getManager().nodes;
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
                    node.activeOutputs.getAll().forEach((output) => {
                        if (output.label) {
                            outputLabels.push(output.label);
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
                case "onHistoryDatasetId":
                    this.onHistoryDatasetId(item.id);
                    break;
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
                case "onVisualizationId":
                    this.onVisualizationId(item.id);
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
        onVisualizationId(argumentName) {
            this.selectedArgumentName = argumentName;
            this.selectedType = "visualization_id";
            this.selectedPayload = this.visualizationIndex[argumentName];
            this.selectedLabels = this.getOutputs();
            this.selectedShow = true;
        },
        onHistoryId(argumentName) {
            this.selectedArgumentName = argumentName;
            this.selectedType = "history_id";
            this.selectedShow = true;
        },
        onHistoryDatasetId(argumentName) {
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
                .get(`${getAppRoot()}api/plugins?embeddable=True`)
                .then(({ data }) => {
                    this.visualizationSection.elems = data.map((x) => {
                        return {
                            id: x.name,
                            name: x.html,
                            description: x.description,
                            logo: x.logo ? `${getAppRoot()}${x.logo}` : null,
                            emitter: "onVisualizationId",
                        };
                    });
                    this.visualizationIndex = {};
                    data.forEach((element) => {
                        this.visualizationIndex[element.name] = element;
                    });
                })
                .catch((e) => {
                    this.error = "Failed to load Visualizations.";
                });
        },
    },
};
</script>
