<script setup lang="ts">
import BootstrapVue from "bootstrap-vue";
import { storeToRefs } from "pinia";
import Vue, { computed, ref } from "vue";

import { getHistories, getInvocations, getJobs, getWorkflows } from "@/components/SelectionField/services";
import { useHistoryStore } from "@/stores/historyStore";

import { type WorkflowLabel } from "./Editor/types";

import MarkdownSelector from "./MarkdownSelector.vue";
import DataDialog from "@/components/DataDialog/DataDialog.vue";
import BasicSelectionDialog from "@/components/SelectionDialog/BasicSelectionDialog.vue";
import DatasetCollectionDialog from "@/components/SelectionDialog/DatasetCollectionDialog.vue";

Vue.use(BootstrapVue);

interface MarkdownDialogProps {
    argumentName?: string;
    argumentType?: string;
    argumentPayload?: object;
    labels?: Array<WorkflowLabel>;
}

const props = withDefaults(defineProps<MarkdownDialogProps>(), {
    argumentName: undefined,
    argumentType: undefined,
    argumentPayload: undefined,
    labels: undefined,
});

const emit = defineEmits<{
    (e: "onCancel"): void;
    (e: "onInsert", value: string): void;
}>();

interface SelectTitles {
    labelTitle: string;
}

type SelectType = "job_id" | "invocation_id" | "history_dataset_id" | "history_dataset_collection_id";

const effectiveLabels = computed<Array<WorkflowLabel>>(() => {
    if (!props.labels) {
        return [];
    }
    const selectSteps = props.argumentType == "job_id";
    const filteredLabels: Array<WorkflowLabel> = [];
    for (const label of props.labels) {
        if (selectSteps && label.type == "step") {
            filteredLabels.push(label);
        } else if (!selectSteps && label.type != "step") {
            filteredLabels.push(label);
        }
    }
    return filteredLabels;
});

const hasLabels = computed(() => props.labels !== undefined);

const selectorConfig = {
    job_id: {
        labelTitle: "Step",
    },
    invocation_id: {
        labelTitle: "Step",
    },
    history_dataset_id: {
        labelTitle: "Dataset (Input/Output)",
    },
    history_dataset_collection_id: {
        labelTitle: "Dataset Collection (Input/Output)",
    },
};

const selectedShow = ref(false);
const workflowShow = ref(false);
const historyShow = ref(false);
const jobShow = ref(false);
const invocationShow = ref(false);
const dataShow = ref(false);
const dataCollectionShow = ref(false);
const { currentHistoryId } = storeToRefs(useHistoryStore());

const selectedLabelTitle = computed(() => {
    const config: SelectTitles = selectorConfig[props.argumentType as SelectType] as SelectTitles;
    return (config && config.labelTitle) || "Select Label";
});

function onData(response: unknown) {
    dataShow.value = false;
    emit("onInsert", `${props.argumentName}(history_dataset_id=${response})`);
}

interface ObjectReference {
    id: string;
}

function onDataCollection(response: ObjectReference) {
    dataCollectionShow.value = false;
    emit("onInsert", `${props.argumentName}(history_dataset_collection_id=${response.id})`);
}

function onJob(response: ObjectReference) {
    jobShow.value = false;
    emit("onInsert", `${props.argumentName}(job_id=${response.id})`);
}

function onInvocation(response: ObjectReference) {
    invocationShow.value = false;
    emit("onInsert", `${props.argumentName}(invocation_id=${response.id})`);
}

function onHistory(response: ObjectReference) {
    historyShow.value = false;
    emit("onInsert", `history_link(history_id=${response.id})`);
}

function onWorkflow(response: ObjectReference) {
    workflowShow.value = false;
    emit("onInsert", `${props.argumentName}(workflow_id=${response.id})`);
}

function onOk(selectedLabel: WorkflowLabel | undefined) {
    const argumentType = props.argumentType ?? "";
    const defaultLabelType: string =
        ["history_dataset_id", "history_dataset_collection_id"].indexOf(argumentType) >= 0 ? "output" : "step";
    const labelText: string = selectedLabel ? selectedLabel.label : "<ENTER LABEL>";
    const labelType: string = selectedLabel ? selectedLabel.type : defaultLabelType;
    selectedShow.value = false;

    function onInsertArgument() {
        emit("onInsert", `${props.argumentName}(${labelType}="${labelText}")`);
    }

    if (props.argumentType == "history_dataset_id") {
        if (hasLabels.value) {
            onInsertArgument();
        } else {
            dataShow.value = true;
        }
    } else if (props.argumentType == "history_dataset_collection_id") {
        if (hasLabels.value) {
            onInsertArgument();
        } else {
            dataCollectionShow.value = true;
        }
    } else if (props.argumentType == "job_id") {
        if (hasLabels.value) {
            onInsertArgument();
        } else {
            jobShow.value = true;
        }
    } else if (props.argumentType == "invocation_id") {
        if (hasLabels.value) {
            onInsertArgument();
        } else {
            invocationShow.value = true;
        }
    }
}

function onCancel() {
    dataCollectionShow.value = false;
    selectedShow.value = false;
    workflowShow.value = false;
    jobShow.value = false;
    invocationShow.value = false;
    dataShow.value = false;
    emit("onCancel");
}

if (props.argumentType == "workflow_id") {
    workflowShow.value = true;
} else if (props.argumentType == "history_id") {
    historyShow.value = true;
} else if (props.argumentType == "history_dataset_id") {
    if (hasLabels.value) {
        selectedShow.value = true;
    } else {
        dataShow.value = true;
    }
} else if (props.argumentType == "history_dataset_collection_id") {
    if (hasLabels.value) {
        selectedShow.value = true;
    } else {
        dataCollectionShow.value = true;
    }
} else if (props.argumentType == "invocation_id") {
    if (hasLabels.value) {
        selectedShow.value = true;
    } else {
        invocationShow.value = true;
    }
} else if (props.argumentType == "job_id") {
    if (hasLabels.value) {
        selectedShow.value = true;
    } else {
        jobShow.value = true;
    }
}
</script>

<template>
    <span>
        <MarkdownSelector
            v-if="selectedShow"
            :initial-value="argumentType"
            :argument-name="argumentName"
            :labels="effectiveLabels"
            :label-title="selectedLabelTitle"
            @onOk="onOk"
            @onCancel="onCancel" />
        <DataDialog
            v-else-if="dataShow && currentHistoryId !== null"
            :history="currentHistoryId"
            format="id"
            @onOk="onData"
            @onCancel="onCancel" />
        <DatasetCollectionDialog
            v-else-if="dataCollectionShow && currentHistoryId !== null"
            :history="currentHistoryId"
            format="id"
            @onOk="onDataCollection"
            @onCancel="onCancel" />
        <BasicSelectionDialog
            v-else-if="jobShow"
            :get-data="getJobs"
            :is-encoded="true"
            title="Job"
            label-key="id"
            @onOk="onJob"
            @onCancel="onCancel" />
        <BasicSelectionDialog
            v-else-if="invocationShow"
            :get-data="getInvocations"
            :is-encoded="true"
            title="Invocation"
            label-key="id"
            @onOk="onInvocation"
            @onCancel="onCancel" />
        <BasicSelectionDialog
            v-else-if="workflowShow"
            :get-data="getWorkflows"
            title="Workflow"
            leaf-icon="fa fa-sitemap fa-rotate-270"
            label-key="name"
            @onOk="onWorkflow"
            @onCancel="onCancel" />
        <BasicSelectionDialog
            v-else-if="historyShow"
            :get-data="getHistories"
            title="History"
            label-key="name"
            @onOk="onHistory"
            @onCancel="onCancel" />
    </span>
</template>
