<template>
    <span>
        <MarkdownSelector
            v-if="selectedShow"
            :initial-value="argumentType"
            :argument-name="argumentName"
            :labels="labels"
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
            @onCancel="onCancel"
        />
        <BasicSelectionDialog
            v-if="invocationShow"
            :get-data="getInvocations"
            :is-encoded="true"
            title="Invocation"
            label-key="id"
            @onOk="onInvocation"
            @onCancel="onCancel"
        />
        <BasicSelectionDialog
            v-if="workflowShow"
            :get-data="getWorkflows"
            title="Workflow"
            leaf-icon="fa fa-sitemap fa-rotate-270"
            label-key="name"
            @onOk="onWorkflow"
            @onCancel="onCancel"
        />
    </span>
</template>

<script>
import axios from "axios";
import Vue from "vue";
import BootstrapVue from "bootstrap-vue";
import { getAppRoot } from "onload/loadConfig";
import { dialog, datasetCollectionDialog } from "utils/data";
import MarkdownSelector from "./MarkdownSelector";
import BasicSelectionDialog from "components/SelectionDialog/BasicSelectionDialog";

Vue.use(BootstrapVue);

export default {
    components: {
        MarkdownSelector,
        BasicSelectionDialog,
    },
    props: {
        argumentName: {
            type: String,
            default: null,
        },
        argumentType: {
            type: String,
            default: null,
        },
        labels: {
            type: Array,
            default: null,
        },
        isWorkflow: {
            type: Boolean,
            default: false,
        },
    },
    data() {
        return {
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
            jobsUrl: `${getAppRoot()}api/jobs`,
            workflowsUrl: `${getAppRoot()}api/workflows`,
            invocationsUrl: `${getAppRoot()}api/invocations`,
            selectedShow: false,
            workflowShow: false,
            jobShow: false,
            invocationShow: false,
        };
    },
    computed: {
        selectedLabelTitle() {
            const config = this.selectorConfig[this.argumentType];
            return (config && config.labelTitle) || "Select Label";
        },
        selectedSelectTitle() {
            const config = this.selectorConfig[this.argumentType];
            return (config && config.selectTitle) || "Select Item";
        },
    },
    created() {
        if (this.argumentType == "workflow_id") {
            this.workflowShow = true;
        } else if (this.argumentType == "history_dataset_id") {
            this.selectedShow = true;
        } else if (this.argumentType == "history_dataset_collection_id") {
            this.selectedShow = true;
        } else if (this.argumentType == "invocation_id") {
            this.invocationShow = true;
        } else if (this.argumentType == "job_id") {
            this.jobShow = true;
        }
    },
    methods: {
        getInvocations() {
            return axios.get(this.invocationsUrl);
        },
        getJobs() {
            return axios.get(this.jobsUrl);
        },
        getWorkflows() {
            return axios.get(this.workflowsUrl);
        },
        onJob(response) {
            this.jobShow = false;
            const argument = this.argumentName;
            this.$emit("onInsert", `${argument}(job_id=${response.id})`);
        },
        onInvocation(response) {
            this.invocationShow = false;
            const argument = this.argumentName;
            this.$emit("onInsert", `${argument}(invocation_id=${response.id})`);
        },
        onWorkflow(response) {
            this.workflowShow = false;
            this.$emit("onInsert", `workflow_display(workflow_id=${response.id})`);
        },
        onOk(selectedLabel) {
            const argumentType = this.argumentType;
            this.selectedShow = false;
            const argumentName = this.argumentName;
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
            this.workflowShow = false;
            this.jobShow = false;
            this.invocationShow = false;
            this.$emit("onCancel");
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
