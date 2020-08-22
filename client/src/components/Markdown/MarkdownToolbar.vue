<template>
    <span>
        <b-dropdown
            v-for="(categoryName, categoryKey) in categoryNames"
            :key="categoryKey"
            no-caret
            right
            role="button"
            variant="link"
            :title="categoryName.title"
            v-b-tooltip.hover.bottom
        >
            <template v-slot:button-content>
                <span :class="['fa', categoryName.icon]" />
            </template>
            <b-dropdown-item
                v-for="argumentName in categories[categoryKey]"
                :key="argumentName"
                href="#"
                @click="onInsert(argumentName)"
            >
                <span :class="['fa fa-fw mr-1', icons[argumentName]]" />
                {{ titles[argumentName] }}
            </b-dropdown-item>
        </b-dropdown>
        <MarkdownSelector
            v-if="selectedShow"
            :initial-value="selectedType"
            :argument-name="selectedArgumentName"
            :labels="selectedLabels"
            :label-title="selectedLabelTitle"
            :select-title="selectedSelectTitle"
            @onOk="onOk"
            @onCancel="onCancel"
        />
        <BasicSelectionDialog
            v-if="jobShow"
            :get-data="getJobs"
            :is-encoded="true"
            title="Job"
            label-key="id"
            @onOk="onJob"
            @onCancel="onJobCancel"
        />
        <BasicSelectionDialog
            v-if="invocationShow"
            :get-data="getInvocations"
            :is-encoded="true"
            title="Invocation"
            label-key="id"
            @onOk="onInvocation"
            @onCancel="onInvocationCancel"
        />
        <BasicSelectionDialog
            v-if="workflowShow"
            :get-data="getWorkflows"
            title="Workflow"
            leaf-icon="fa fa-sitemap fa-rotate-270"
            label-key="name"
            @onOk="onWorkflow"
            @onCancel="onWorkflowCancel"
        />
    </span>
</template>

<script>
import axios from "axios";
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { getAppRoot } from "onload/loadConfig";
import MarkdownSelector from "./MarkdownSelector";
import { dialog, datasetCollectionDialog } from "utils/data";
import BasicSelectionDialog from "components/SelectionDialog/BasicSelectionDialog";

Vue.use(BootstrapVue);

export default {
    components: {
        MarkdownSelector,
        BasicSelectionDialog,
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
            categories: {},
            categoryNames: {
                history_dataset: {
                    title: "Insert Datasets",
                    icon: "fa-file",
                },
                tool: {
                    title: "Insert Jobs",
                    icon: "fa-wrench",
                },
                workflow: {
                    title: "Insert Workflows",
                    icon: "fa-sitemap fa-rotate-270",
                },
                others: {
                    title: "Insert Others",
                    icon: "fa-tools",
                },
            },
            categoryKeys: {
                history_dataset_: "history_dataset",
                history_dataset_collection_: "history_dataset",
                tool_: "tool",
                job_: "tool",
                invocation_: "workflow",
                workflow_: "workflow",
            },
            icons: {
                history_dataset_display: "fa-file-o",
                history_dataset_collection_display: "fa-folder-o",
                history_dataset_as_image: "fa-image",
                history_dataset_link: "fa-link",
                history_dataset_info: "fa-info",
                invocation_time: "fa-clock",
                tool_stderr: "fa-bug",
                tool_stdout: "fa-quote-right",
                job_metrics: "fa-tachometer-alt",
                job_parameters: "fa-tasks",
                generate_time: "fa-stopwatch",
                history_dataset_name: "fa-signature",
                invocation_inputs: "fa-arrow-right",
                invocation_outputs: "fa-arrow-left",
                generate_galaxy_version: "fa-certificate",
                workflow_display: "fa-sitemap fa-rotate-270",
            },
            selectorConfig: {
                job_id: {
                    labelTitle: "Select Step Label",
                    selectTitle: "Select Job by Identifier",
                },
                invocation_id: {
                    labelTitle: "Select Step Label",
                    selectTitle: "Select Invocation by Identifier",
                },
                history_dataset_id: {
                    labelTitle: "Select Output Label",
                    selectTitle: "Select Dataset from History",
                },
                history_dataset_collection_id: {
                    labelTitle: "Select Output Label",
                    selectTitle: "Select Dataset Collection from History",
                },
            },
            titles: {},
            jobsUrl: `${getAppRoot()}api/jobs`,
            workflowsUrl: `${getAppRoot()}api/workflows`,
            invocationsUrl: `${getAppRoot()}api/invocations`,
            selectedShow: false,
            workflowShow: false,
            jobShow: false,
            invocationShow: false,
            selectedArgumentName: null,
            selectedType: null,
            selectedLabel: null,
        };
    },
    computed: {
        hasNodes() {
            return !!this.nodes;
        },
        selectedLabelTitle() {
            const config = this.selectorConfig[this.selectedType];
            return (config && config.labelTitle) || "Select Label";
        },
        selectedSelectTitle() {
            const config = this.selectorConfig[this.selectedType];
            return (config && config.selectTitle) || "Select Item";
        },
    },
    created() {
        for (const argumentName in this.validArguments) {
            let categoryName = "";
            for (const categoryKey in this.categoryKeys) {
                if (argumentName.startsWith(categoryKey)) {
                    categoryName = this.categoryKeys[categoryKey];
                    break;
                }
            }
            if (!categoryName) {
                categoryName = "others";
            }
            this.categories[categoryName] = this.categories[categoryName] || [];
            this.categories[categoryName].push(argumentName);
            this.titles[argumentName] = this.getArgumentTitle(argumentName);
        }
        for (const categoryName in this.categories) {
            this.categories[categoryName] = this.categories[categoryName].sort();
        }
    },
    methods: {
        onJob(response) {
            this.jobShow = false;
            const argument = this.selectedArgumentName;
            this.$emit("onInsert", `${argument}(job_id=${response.id})`);
        },
        onInvocation(response) {
            this.invocationShow = false;
            const argument = this.selectedArgumentName;
            this.$emit("onInsert", `${argument}(invocation_id=${response.id})`);
        },
        onWorkflow(response) {
            this.workflowShow = false;
            this.$emit("onInsert", `workflow_display(workflow_id=${response.id})`);
        },
        getInvocations() {
            return axios.get(this.invocationsUrl);
        },
        getJobs() {
            return axios.get(this.jobsUrl);
        },
        getWorkflows() {
            return axios.get(this.workflowsUrl);
        },
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
        onOk(argumentType, selectedLabel) {
            this.selectedShow = false;
            const argumentName = this.selectedArgumentName;
            if (argumentType == "history_dataset_id") {
                if (selectedLabel) {
                    this.$emit("onInsert", `${argumentName}(output="${selectedLabel}")`);
                } else {
                    this.selectDataset(argumentName);
                }
            } else if (argumentType == "history_dataset_collection_id") {
                if (selectedLabel) {
                    this.$emit("onInsert", `${argumentName}(output="${selectedLabel}")`);
                } else {
                    this.selectDatasetCollection(argumentName);
                }
            } else if (argumentType == "job_id") {
                if (selectedLabel) {
                    this.$emit("onInsert", `${argumentName}(step="${selectedLabel}")`);
                } else {
                    this.jobShow = true;
                }
            } else if (argumentType == "invocation_id") {
                if (selectedLabel) {
                    this.$emit("onInsert", `${argumentName}(step="${selectedLabel}")`);
                } else {
                    this.invocationShow = true;
                }
            }
        },
        onCancel() {
            this.selectedShow = false;
        },
        onWorkflowCancel() {
            this.workflowShow = false;
        },
        onJobCancel() {
            this.jobShow = false;
        },
        onInvocationCancel() {
            this.invocationShow = false;
        },
        onInsert(argumentName) {
            this.selectedArgumentName = argumentName;
            const arg = this.validArguments[argumentName];
            if (arg.length == 0) {
                this.$emit("onInsert", `${argumentName}()`);
            } else if (arg.includes("workflow_id")) {
                this.workflowShow = true;
            } else if (arg.includes("job_id")) {
                if (this.hasNodes) {
                    this.selectedType = "job_id";
                    this.selectedLabels = this.getSteps();
                    this.selectedShow = true;
                } else {
                    this.onOk("job_id");
                }
            } else if (arg.includes("invocation_id")) {
                if (this.hasNodes) {
                    this.selectedType = "invocation_id";
                    this.selectedLabels = this.getSteps();
                    this.selectedShow = true;
                } else {
                    this.onOk("invocation_id");
                }
            } else if (arg.includes("history_dataset_id")) {
                if (this.hasNodes) {
                    this.selectedType = "history_dataset_id";
                    this.selectedLabels = this.getOutputs();
                    this.selectedShow = true;
                } else {
                    this.onOk("history_dataset_id");
                }
            } else if (arg.includes("history_dataset_collection_id")) {
                if (this.hasNodes) {
                    this.selectedType = "history_dataset_collection_id";
                    this.selectedLabels = this.getOutputs();
                    this.selectedShow = true;
                } else {
                    this.onOk("history_dataset_collection_id");
                }
            } else {
                this.$emit("onInsert", `${argumentName}(${arg.join(", ")}=<ENTER A VALUE>)`);
            }
        },
        selectDataset(galaxyCall) {
            dialog(
                (response) => {
                    const datasetId = response.id;
                    this.$emit("onInsert", `${galaxyCall}(history_dataset_id=${datasetId})`);
                },
                {
                    multiple: false,
                    format: null,
                    library: false,
                }
            );
        },
        selectDatasetCollection(galaxyCall) {
            datasetCollectionDialog((response) => {
                this.$emit("onInsert", `${galaxyCall}(history_dataset_collection_id=${response.id})`);
            }, {});
        },
    },
};
</script>
