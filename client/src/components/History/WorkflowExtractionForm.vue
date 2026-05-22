<script setup lang="ts">
import { faCheck, faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert } from "bootstrap-vue";
import { computed, ref } from "vue";
import { useRouter } from "vue-router/composables";

import {
    extractWorkflowByIds,
    extractWorkflowFromHistory,
    type WorkflowExtractionByIdsPayload,
    type WorkflowExtractionJob,
} from "@/api/histories";
import { useToast } from "@/composables/toast";
import { useHistoryStore } from "@/stores/historyStore";
import { errorMessageAsString } from "@/utils/simple-error";

import {
    isMappedTool,
    isWorkflowExtractionInput,
    type WorkflowExtractionInput,
    type WorkflowExtractionRow,
} from "./WorkflowExtraction/types";

import GFormInput from "../BaseComponents/Form/GFormInput.vue";
import GButton from "../BaseComponents/GButton.vue";
import GModal from "../BaseComponents/GModal.vue";
import BreadcrumbHeading from "../Common/BreadcrumbHeading.vue";
import RenameModal from "../Common/RenameModal.vue";
import JobDetails from "../JobInformation/JobDetails.vue";
import LoadingSpan from "../LoadingSpan.vue";
import WorkflowExtractionCard from "./WorkflowExtraction/WorkflowExtractionCard.vue";
import WorkflowExtractionMessages from "./WorkflowExtraction/WorkflowExtractionMessages.vue";

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
const submitting = ref(false);
const errorMessage = ref<string | null>(null);
const jobsList = ref<WorkflowExtractionRow[]>([]);
const workflowName = ref("");
const renameIndex = ref<number | null>(null);
const warnings = ref<string[]>([]);
const showJobModal = ref(false);
const viewedJobId = ref<string | null>(null);

/** The job (input step) to rename based on the current `renameIndex`. */
const toRenameInput = computed(() => {
    if (renameIndex.value === null || !jobsList.value?.length) {
        return null;
    }
    const job = jobsList.value[renameIndex.value];
    if (job && isWorkflowExtractionInput(job)) {
        return job;
    }
    return null;
});

const submissionDisabled = computed(
    () => submitting.value || hasUnnamedSelectedInputs.value || !workflowName.value.trim() || hasNoSelectedSteps.value,
);

const submissionDisabledMsg = computed(() => {
    if (!workflowName.value.trim()) {
        return "Workflow name is required";
    }
    if (hasUnnamedSelectedInputs.value) {
        return "All selected inputs must have a name";
    }
    if (hasNoSelectedSteps.value) {
        return "At least one workflow step must be selected";
    }
    return "";
});

/** Selected tool jobs partitioned by ICJ membership. Mapped jobs collapse to
 *  their implicit_collection_jobs_id (deduped); non-mapped jobs stay as job_ids. */
const selectedJobBuckets = computed<{ job_ids: string[]; implicit_collection_jobs_ids: string[] }>(() => {
    if (!jobsList.value?.length) {
        return { job_ids: [], implicit_collection_jobs_ids: [] };
    }
    const job_ids: string[] = [];
    const icj_ids: string[] = [];
    const seen_icj = new Set<string>();
    for (const job of jobsList.value) {
        if (!job.checked || job.step_type !== "tool" || !job.id) {
            continue;
        }
        if (isMappedTool(job)) {
            if (!seen_icj.has(job.implicit_collection_jobs_id)) {
                seen_icj.add(job.implicit_collection_jobs_id);
                icj_ids.push(job.implicit_collection_jobs_id);
            }
        } else {
            job_ids.push(job.id);
        }
    }
    return { job_ids, implicit_collection_jobs_ids: icj_ids };
});

/**
 * A parallel mapping for `checked` input step type encoded ids and their `newNames`.
 */
const selectedInputs = computed<
    {
        id: string;
        newName: string;
        history_content_type: "dataset" | "dataset_collection";
    }[]
>(() => {
    if (!jobsList.value?.length) {
        return [];
    }
    const retVal = jobsList.value
        .filter(
            (job): job is WorkflowExtractionInput =>
                job.checked && isWorkflowExtractionInput(job) && (job.outputs?.length ?? 0) > 0,
        )
        .flatMap((job) =>
            job.outputs?.map((output) => ({
                id: output.id,
                newName: job.newName,
                history_content_type: output.history_content_type,
            })),
        )
        .filter((item) => item !== undefined);
    return retVal;
});

/** No workflow steps are selected: the workflow would have no steps */
const hasNoSelectedSteps = computed(() => !jobsList.value?.some((job) => job.checked));

/** For any inputs selected for inclusion as workflow steps, check if any are missing a name/label */
const hasUnnamedSelectedInputs = computed(() => {
    return selectedInputs.value.some((input) => !input.newName);
});

extractWorkflow();

function toWorkflowExtractionRow(job: WorkflowExtractionJob): WorkflowExtractionRow {
    const checked = job.checked ?? false;
    if (job.step_type === "tool") {
        return {
            ...job,
            checked,
            step_type: "tool",
        };
    } else {
        return {
            ...job,
            checked,
            step_type: job.step_type,
            newName: getInputName(job) || "",
        };
    }
}

function getInputName(job: WorkflowExtractionJob): string | undefined {
    if (job.outputs?.length && job.outputs[0]) {
        const output = job.outputs[0];
        return output.name || `Input ${output.hid}`;
    }
}

function getSelectedInputs(type: "dataset" | "dataset_collection"): { ids: string[]; names: string[] } {
    const inputs = selectedInputs.value.filter(
        (input) => input.history_content_type === type && Boolean(input.newName),
    );
    return {
        ids: inputs.map((input) => input.id),
        names: inputs.map((input) => input.newName),
    };
}

async function extractWorkflow() {
    try {
        const result = await extractWorkflowFromHistory(props.historyId);
        if (result.jobs) {
            jobsList.value = result.jobs.map(toWorkflowExtractionRow);
        }

        warnings.value = result.warnings || [];
    } catch (error) {
        errorMessage.value = errorMessageAsString(error);
    } finally {
        loading.value = false;
    }
}

function onJobRename(index: number) {
    if (!jobsList.value?.length) {
        return;
    }

    renameIndex.value = index;
}

function onJobSelect(index: number) {
    if (!jobsList.value?.length) {
        return;
    }
    const job = jobsList.value[index];
    if (job) {
        job.checked = !job.checked;
    }
}

function onViewJob(jobId: string) {
    viewedJobId.value = jobId;
    showJobModal.value = true;
}

async function renameInput(newName: string) {
    if (!jobsList.value?.length) {
        throw new Error("No jobs available to rename");
    }
    if (renameIndex.value === null) {
        throw new Error("Invalid job index");
    }

    if (!toRenameInput.value) {
        throw new Error("Job not found or is not an input");
    }

    // Instead of using the computed `toRenameInput`, we directly update the `newName` in the `jobsList`
    // to ensure reactivity and that the change is reflected in the UI immediately.
    (jobsList.value[renameIndex.value] as WorkflowExtractionInput).newName = newName;
}

async function submitWorkflow() {
    try {
        if (submissionDisabled.value) {
            Toast.error(submissionDisabledMsg.value || "Cannot submit workflow extraction", "Submission Disabled");
            return;
        }
        errorMessage.value = null;
        submitting.value = true;

        const selectedDatasets = getSelectedInputs("dataset");
        const selectedDatasetCollections = getSelectedInputs("dataset_collection");

        const payload: WorkflowExtractionByIdsPayload = {
            workflow_name: workflowName.value.trim(),
            job_ids: selectedJobBuckets.value.job_ids,
            implicit_collection_jobs_ids: selectedJobBuckets.value.implicit_collection_jobs_ids,
            hda_ids: selectedDatasets.ids,
            hdca_ids: selectedDatasetCollections.ids,
            dataset_names: selectedDatasets.names,
            dataset_collection_names: selectedDatasetCollections.names,
        };

        const data = await extractWorkflowByIds(payload);

        Toast.success("Workflow created successfully", "Success");

        router.push(`/published/workflow?id=${data.id}`);
    } catch (error) {
        errorMessage.value = errorMessageAsString(error);
    } finally {
        submitting.value = false;
    }
}

function stepKind(job: WorkflowExtractionRow): string {
    if (isMappedTool(job)) {
        return "mapped-tool";
    }
    return job.step_type.replace("_", "-");
}
</script>

<template>
    <div class="workflow-extraction-form" data-description="workflow-extraction-form">
        <div class="workflow-extraction-header">
            <BreadcrumbHeading :items="breadcrumbItems" />

            <BAlert v-if="errorMessage" variant="danger" show>{{ errorMessage }}</BAlert>
            <BAlert v-if="loading" variant="info" show>
                <LoadingSpan message="Extracting workflow from history" />
            </BAlert>
            <div v-if="!loading && jobsList.length" class="d-flex flex-column flex-gapy-1">
                <div class="workflow-extraction-actions">
                    <GFormInput
                        v-model="workflowName"
                        data-description="workflow-name-input"
                        placeholder="Please provide a name for the workflow"
                        :disabled="submitting"
                        @keydown.enter.prevent="submitWorkflow" />

                    <GButton
                        color="blue"
                        tooltip
                        data-description="create-workflow-button"
                        title="Create the extracted workflow"
                        :disabled="submissionDisabled"
                        :disabled-title="submissionDisabledMsg"
                        @click="submitWorkflow">
                        <FontAwesomeIcon :icon="submitting ? faSpinner : faCheck" :spin="submitting" fixed-width />
                        {{ submitting ? "Creating..." : "Create Workflow" }}
                    </GButton>
                </div>
                <WorkflowExtractionMessages :warnings="warnings" />
            </div>
            <BAlert
                v-if="!loading && !errorMessage && !jobsList.length"
                data-description="no-workflow-message"
                variant="info"
                show>
                No workflow could be extracted from this history.
            </BAlert>
        </div>

        <div v-if="jobsList.length" class="workflow-extraction-list">
            <WorkflowExtractionCard
                v-for="(job, index) in jobsList"
                :id="`workflow-extraction-job-${index}`"
                :key="index"
                :job="job"
                :data-step-type="job.step_type"
                :data-job-id="job.id || undefined"
                :data-icj-id="isMappedTool(job) ? job.implicit_collection_jobs_id : undefined"
                :data-step-kind="stepKind(job)"
                @rename="onJobRename(index)"
                @select="onJobSelect(index)"
                @view-job="onViewJob" />
        </div>

        <RenameModal
            v-if="toRenameInput"
            item-type="input"
            :name="toRenameInput.newName"
            :rename-action="renameInput"
            @close="renameIndex = null" />

        <GModal :show.sync="showJobModal" title="View Job" fixed-height size="medium" @close="viewedJobId = null">
            <JobDetails v-if="viewedJobId" :job-id="viewedJobId" />
        </GModal>
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

    .workflow-extraction-list {
        flex-grow: 1;
        overflow: auto;
    }
}
</style>
