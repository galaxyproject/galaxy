<script setup lang="ts">
import { BAlert, BBadge } from "bootstrap-vue";
import { computed, ref } from "vue";
import { useRouter } from "vue-router/composables";

import {
    extractWorkflowFromHistory,
    submitWorkflowExtraction,
    type WorkflowExtractionJob,
    type WorkflowExtractionPayload,
} from "@/api/histories";
import { useToast } from "@/composables/toast";
import { useHistoryStore } from "@/stores/historyStore";
import { errorMessageAsString } from "@/utils/simple-error";

import type { TableField } from "../Common/GTable.types";
import type { ClientWorkflowExtractionJob } from "./WorkflowExtraction/types";

import GFormInput from "../BaseComponents/Form/GFormInput.vue";
import GButton from "../BaseComponents/GButton.vue";
import BreadcrumbHeading from "../Common/BreadcrumbHeading.vue";
import GTable from "../Common/GTable.vue";
import LoadingSpan from "../LoadingSpan.vue";
import WorkflowExtractionNode from "./WorkflowExtraction/WorkflowExtractionNode.vue";
import GenericHistoryItem from "@/components/History/Content/GenericItem.vue";

const props = defineProps<{
    historyId: string;
}>();

const router = useRouter();

const Toast = useToast();

const historyStore = useHistoryStore();
const historyName = computed(() => historyStore.getHistoryNameById(props.historyId));

const breadcrumbItems = computed(() => [
    { title: "Histories", to: "/histories/list" },
    {
        title: historyName.value,
        to: `/histories/view?id=${props.historyId}`,
        superText: historyStore.currentHistoryId === props.historyId ? "current" : undefined,
    },
    { title: "Extract Workflow" },
]);

const loading = ref(true);
const errorMessage = ref<string | null>(null);
const jobsList = ref<ClientWorkflowExtractionJob[]>([]);
const workflowName = ref("");

/** The indices in the jobsList that are currently selected
 * (regardless of whether they are inputs or steps)
 */
const selectedIndices = computed(() => {
    if (!jobsList.value?.length) {
        return [];
    }
    return jobsList.value.map((job, index) => (job.checked ? index : -1)).filter((i) => i !== -1);
});

const submissionDisabled = computed(() => hasUnnamedSelectedInputs.value || !workflowName.value.trim());

const submissionDisabledMsg = computed(() => {
    if (!workflowName.value.trim()) {
        return "Workflow name is required";
    }
    if (hasUnnamedSelectedInputs.value) {
        return "All selected inputs must have a name";
    }
    return "";
});

/** Selected job ids for workflow steps (not inputs) */
const selectedJobIds = computed<Array<string>>(() => {
    if (!jobsList.value?.length) {
        return [];
    }
    return jobsList.value
        .filter((job) => job.checked && job.stepType === "tool")
        .map((job) => job.id)
        .filter((id): id is string => Boolean(id));
});

/**
 * A parallel mapping for `checked` input step type `hid`s and their `newNames`
 */
const selectedInputs = computed<
    {
        hid: number;
        newName: string | undefined;
        history_content_type: "dataset" | "dataset_collection";
    }[]
>(() => {
    if (!jobsList.value?.length) {
        return [];
    }
    const retVal = jobsList.value
        .filter((job) => job.checked && job.stepType !== "tool" && job.outputs?.length)
        .flatMap((job) =>
            job.outputs?.map((output) => ({
                hid: output.hid,
                newName: "newName" in job ? job.newName : output.name,
                history_content_type: output.history_content_type,
            })),
        )
        .filter((item) => item !== undefined);
    return retVal;
});

const hasUnnamedSelectedInputs = computed(() => {
    return selectedInputs.value.some((input) => !input.newName);
});

const tableFields: TableField[] = [
    {
        key: "tool_name",
        label: "Workflow Step",
    },
    {
        key: "tool_id",
        label: "Rename Input (optional)",
    },
    {
        key: "outputs",
        label: "Outputs",
        width: "25vw",
    },
];

extractWorkflow();

function getStepType(job: WorkflowExtractionJob): ClientWorkflowExtractionJob["stepType"] {
    if (!job.tool_id || Boolean(job.disabled_why)) {
        if (job.outputs?.length === 1 && job.outputs[0]) {
            const output = job.outputs[0];
            return output.history_content_type === "dataset" ? "input_dataset" : "input_collection";
        }
        // Default to input_dataset for jobs without a tool_id, even if they have multiple outputs
        return "input_dataset";
    }
    return "tool";
}

function getSelectedInputs(type: "dataset" | "dataset_collection"): { hids: number[]; names: string[] } {
    const inputs = selectedInputs.value.filter(
        (input) => input.history_content_type === type && Boolean(input.newName),
    );
    return {
        hids: inputs.map((input) => input.hid),
        names: inputs.map((input) => input.newName ?? ""),
    };
}

async function extractWorkflow() {
    try {
        let unnamedToolIndex = 0;

        const result = await extractWorkflowFromHistory(props.historyId);
        if (result.jobs) {
            jobsList.value = result.jobs.map((job) => {
                const stepType = getStepType(job);
                return {
                    ...job,
                    ...(stepType.includes("input") && {
                        newName: job.tool_name ?? `Workflow Input ${++unnamedToolIndex}`,
                    }),
                    stepType,
                };
            });
        }

        // TODO: Handle/display result.warnings
    } catch (error) {
        errorMessage.value = errorMessageAsString(error);
    } finally {
        loading.value = false;
    }
}

function onRowSelect(event: { item: ClientWorkflowExtractionJob; index: number; selected: boolean }) {
    if (!jobsList.value?.length) {
        return;
    }
    const job = jobsList.value[event.index];
    if (job) {
        job.checked = event.selected;
    }
}

async function submitWorkflow() {
    try {
        if (submissionDisabled.value) {
            Toast.error(submissionDisabledMsg.value || "Cannot submit workflow extraction", "Submission Disabled");
            return;
        }
        loading.value = true;

        const selectedDatasets = getSelectedInputs("dataset");
        const selectedDatasetCollections = getSelectedInputs("dataset_collection");

        const payload: WorkflowExtractionPayload = {
            workflow_name: workflowName.value.trim(),
            job_ids: selectedJobIds.value,
            dataset_hids: selectedDatasets.hids,
            dataset_collection_hids: selectedDatasetCollections.hids,
            dataset_names: selectedDatasets.names,
            dataset_collection_names: selectedDatasetCollections.names,
        };

        const data = await submitWorkflowExtraction(props.historyId, payload);

        router.push(`/workflows/edit?id=${data.id}`);
    } catch (error) {
        errorMessage.value = errorMessageAsString(error);
    } finally {
        loading.value = false;
    }
}
</script>

<template>
    <div class="workflow-extraction-form">
        <div class="workflow-extraction-header">
            <BreadcrumbHeading :items="breadcrumbItems" />

            <BAlert v-if="errorMessage" variant="danger" show>{{ errorMessage }}</BAlert>
            <BAlert v-else-if="loading" variant="info" show>
                <LoadingSpan message="Extracting workflow from history" />
            </BAlert>
            <div v-else-if="jobsList.length" class="d-flex flex-column flex-gapy-1">
                <div class="workflow-extraction-actions">
                    <GFormInput
                        v-model="workflowName"
                        placeholder="Please provide a name for the workflow"
                        @keydown.enter.prevent="submitWorkflow" />

                    <GButton
                        tooltip
                        title="Create the extracted workflow"
                        :disabled="submissionDisabled"
                        :disabled-title="submissionDisabledMsg"
                        @click="submitWorkflow">
                        Create Workflow
                    </GButton>
                </div>
                <div>
                    The following table contains each tool that was run to create the datasets in your current history.
                    Please select those that you wish to include in the workflow.
                </div>
            </div>
            <BAlert v-else variant="info" show> No workflow could be extracted from this history. </BAlert>
        </div>

        <div v-if="jobsList.length" class="workflow-extraction-table">
            <GTable
                :hover="false"
                selectable
                select-checkbox-title="Include as a step in the workflow"
                :selected-items="selectedIndices"
                :striped="false"
                :fields="tableFields"
                :items="jobsList"
                @row-select="onRowSelect">
                <template v-slot:cell(tool_name)="{ item }">
                    <WorkflowExtractionNode :job="item" />
                </template>

                <template v-slot:cell(tool_id)="{ item }">
                    <GFormInput
                        v-if="'newName' in item"
                        v-model="item.newName"
                        :disabled="!item.checked"
                        placeholder="Input must have a name" />

                    <BBadge v-else>Workflow Step</BBadge>
                </template>

                <template v-slot:cell(outputs)="{ item }">
                    <div v-for="(output, index) in item.outputs" :key="index">
                        <GenericHistoryItem
                            :item-id="output.id"
                            :item-src="output.history_content_type === 'dataset' ? 'hda' : 'hdca'" />
                    </div>
                </template>
            </GTable>
        </div>
    </div>
</template>

<style scoped lang="scss">
.workflow-extraction-form {
    display: flex;
    flex-direction: column;
    height: 100%;

    .workflow-extraction-header {
        display: flex;
        flex-direction: column;

        .workflow-extraction-actions {
            display: flex;
            align-items: center;
            gap: 0.5rem;

            input {
                width: 100%;
            }
            button {
                white-space: nowrap;
            }
        }
    }

    .workflow-extraction-table {
        flex-grow: 1;
        overflow: auto;
    }
}
</style>
