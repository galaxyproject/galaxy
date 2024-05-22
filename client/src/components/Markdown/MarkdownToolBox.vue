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
                <ToolSection v-if="isWorkflow" :category="historyInEditorSection" :expanded="true" @onClick="onClick" />
                <ToolSection v-else :category="historySection" :expanded="true" @onClick="onClick" />
                <ToolSection :category="jobSection" :expanded="true" @onClick="onClick" />
                <ToolSection
                    v-if="isWorkflow"
                    :category="workflowInEditorSection"
                    :expanded="true"
                    @onClick="onClick" />
                <ToolSection v-else :category="workflowSection" :expanded="true" @onClick="onClick" />
                <ToolSection :category="linksSection" :expanded="false" @onClick="onClick" />
                <ToolSection :category="otherSection" :expanded="true" @onClick="onClick" />
                <ToolSection
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
            :labels="workflowLabels"
            :use-labels="isWorkflow"
            @onInsert="onInsert"
            @onCancel="onCancel" />
    </div>
</template>

<script>
import axios from "axios";
import BootstrapVue from "bootstrap-vue";
import ToolSection from "components/Panels/Common/ToolSection";
import { getAppRoot } from "onload/loadConfig";
import Vue from "vue";

import { directiveEntry } from "./directives.ts";
import { fromSteps } from "./labels.ts";
import MarkdownDialog from "./MarkdownDialog";

Vue.use(BootstrapVue);

function historySharedElements(mode) {
    return [
        directiveEntry("history_dataset_display", mode, {
            emitter: "onHistoryDatasetId",
        }),
        directiveEntry("history_dataset_collection_display", mode, {
            emitter: "onHistoryCollectionId",
        }),
        directiveEntry("history_dataset_as_image", mode, {
            emitter: "onHistoryDatasetId",
        }),
        directiveEntry("history_dataset_index", mode, {
            emitter: "onHistoryDatasetId",
        }),
        directiveEntry("history_dataset_embedded", mode, {
            emitter: "onHistoryDatasetId",
        }),
        directiveEntry("history_dataset_as_table", mode, {
            emitter: "onHistoryDatasetId",
        }),
        directiveEntry("history_dataset_type", mode, {
            emitter: "onHistoryDatasetId",
        }),
        directiveEntry("history_dataset_link", mode, {
            emitter: "onHistoryDatasetId",
        }),
        directiveEntry("history_dataset_name", mode, {
            emitter: "onHistoryDatasetId",
        }),
        directiveEntry("history_dataset_peek", mode, {
            emitter: "onHistoryDatasetId",
        }),
        directiveEntry("history_dataset_info", mode, {
            emitter: "onHistoryDatasetId",
        }),
    ];
}

export default {
    components: {
        MarkdownDialog,
        ToolSection,
    },
    props: {
        steps: {
            type: Object,
            default: null,
        },
    },
    data() {
        return {
            selectedArgumentName: null,
            selectedType: null,
            selectedShow: false,
            selectedPayload: null,
            visualizationIndex: {},
            error: null,
            historySection: {
                title: "History",
                name: "history",
                elems: [
                    ...historySharedElements("page"),
                    directiveEntry("history_link", "page", {
                        emitter: "onHistoryId",
                    }),
                ],
            },
            historyInEditorSection: {
                title: "History",
                name: "history",
                elems: [...historySharedElements("report"), directiveEntry("history_link", "report")],
            },
            workflowSection: {
                title: "Workflow",
                name: "workflow",
                elems: [
                    directiveEntry("invocation_time", "page", {
                        emitter: "onInvocationId",
                    }),
                    directiveEntry("workflow_display", "page", {
                        emitter: "onWorkflowId",
                    }),
                    directiveEntry("workflow_license", "page", {
                        emitter: "onWorkflowId",
                    }),
                    directiveEntry("workflow_image", "page", {
                        emitter: "onWorkflowId",
                    }),
                ],
            },
            workflowInEditorSection: {
                title: "Workflow",
                name: "workflow",
                elems: [
                    directiveEntry("invocation_inputs", "report"),
                    directiveEntry("invocation_outputs", "report"),
                    directiveEntry("invocation_time", "report"),
                    directiveEntry("workflow_display", "report"),
                    directiveEntry("workflow_license", "report"),
                    directiveEntry("workflow_image", "report"),
                ],
            },
            linksSection: {
                title: "Galaxy Instance Links",
                name: "links",
                elems: [
                    {
                        id: "instance_access_link",
                        name: "Access",
                        description: "(link used to access this Galaxy)",
                    },
                    {
                        id: "instance_resources_link",
                        name: "Resources",
                        description: "(link for more information about this Galaxy)",
                    },
                    {
                        id: "instance_help_link",
                        name: "Help",
                        description: "(link for finding help content for this Galaxy)",
                    },
                    {
                        id: "instance_support_link",
                        name: "Support",
                        description: "(link for support for this Galaxy)",
                    },
                    {
                        id: "instance_citation_link",
                        name: "Citation",
                        description: "(link describing how to cite this Galaxy instance)",
                    },
                    {
                        id: "instance_terms_link",
                        name: "Terms and Conditions",
                        description: "(link describing terms and conditions for using this Galaxy instance)",
                    },
                    {
                        id: "instance_organization_link",
                        name: "Organization",
                        description: "(link describing organization that runs this Galaxy instance)",
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
            return !!this.steps;
        },
        mode() {
            return this.isWorkflow ? "report" : "page";
        },
        hasVisualizations() {
            return this.visualizationSection.elems.length > 0;
        },
        otherSection() {
            return {
                title: "Miscellaneous",
                name: "others",
                elems: [
                    directiveEntry("generate_galaxy_version", this.mode),
                    directiveEntry("generate_time", this.mode),
                ],
            };
        },
        jobSection() {
            return {
                title: "Jobs",
                name: "jobs",
                elems: [
                    directiveEntry("job_metrics", this.mode, {
                        emitter: "onJobId",
                    }),
                    directiveEntry("job_parameters", this.mode, {
                        emitter: "onJobId",
                    }),
                    directiveEntry("tool_stdout", this.mode, {
                        emitter: "onJobId",
                    }),
                    directiveEntry("tool_stderr", this.mode, {
                        emitter: "onJobId",
                    }),
                ],
            };
        },
        workflowLabels() {
            return fromSteps(this.steps);
        },
    },
    created() {
        this.getVisualizations();
    },
    methods: {
        getSteps() {
            const steps = [];
            this.steps &&
                Object.values(this.steps).forEach((step) => {
                    if (step.label) {
                        steps.push(step.label);
                    }
                });
            return steps;
        },
        getOutputs(filterByType = undefined) {
            const outputLabels = [];
            this.steps &&
                Object.values(this.steps).forEach((step) => {
                    step.workflow_outputs.forEach((workflowOutput) => {
                        if (workflowOutput.label) {
                            if (!filterByType || this.stepOutputMatchesType(step, workflowOutput, filterByType)) {
                                outputLabels.push(workflowOutput.label);
                            }
                        }
                    });
                });
            return outputLabels;
        },
        stepOutputMatchesType(step, workflowOutput, type) {
            return Boolean(
                step.outputs.find((output) => output.name === workflowOutput.output_name && output.type === type)
            );
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
            this.selectedLabels = this.getOutputs("data");
            this.selectedShow = true;
        },
        onHistoryCollectionId(argumentName) {
            this.selectedArgumentName = argumentName;
            this.selectedType = "history_dataset_collection_id";
            this.selectedLabels = this.getOutputs("collection");
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
            this.selectedShow = true;
        },
        onInvocationId(argumentName) {
            this.selectedArgumentName = argumentName;
            this.selectedType = "invocation_id";
            this.selectedShow = true;
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
