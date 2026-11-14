<script setup lang="ts">
import { useDebounceFn } from "@vueuse/core";
import { computed, ref, watch } from "vue";
import Multiselect from "vue-multiselect";

import { loadWorkflows, type RefactorRequestAction, type WorkflowSummary, type WorkflowVersion } from "@/api/workflows";
import { getVersions } from "@/components/Workflow/Editor/modules/services";
import type { TrsVersionReference } from "@/components/Workflow/Import/types";
import { errorMessageAsString } from "@/utils/simple-error";

import { workflowVersionText } from "./workflowVersionText";

import FormSubworkflowReplaceTrs from "./FormSubworkflowReplaceTrs.vue";
import GFormInput from "@/components/BaseComponents/Form/GFormInput.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import GSelect from "@/components/BaseComponents/GSelect.vue";

interface WorkflowOption {
    value: string;
    text: string;
}

const props = defineProps<{
    stepId: number;
    /** The stored workflow being edited, which can't be its own step */
    workflowId?: string;
}>();

const emit = defineEmits<{
    (e: "onAttemptRefactor", actions: RefactorRequestAction[]): void;
}>();

const CONNECTIONS_HELP = "Connections stay on inputs and outputs with the same names.";
const IMPORT_HELP = "The workflow is imported into your account as a hidden workflow, and the step uses the import.";
const SEARCH_DELAY_MS = 400;

const expanded = ref(false);
const source = ref<"galaxy" | "trs" | "url">("galaxy");
const trsTarget = ref<TrsVersionReference | null>(null);
const url = ref("");
const workflows = ref<WorkflowSummary[]>([]);
const loading = ref(false);
const error = ref<string | null>(null);
const selectedWorkflow = ref<WorkflowOption | null>(null);
const selectedWorkflowId = computed(() => selectedWorkflow.value?.value ?? null);
const versions = ref<WorkflowVersion[]>([]);
const selectedVersion = ref<string | null>(null);

const workflowOptions = computed<WorkflowOption[]>(() =>
    workflows.value
        .filter((workflow) => workflow.id !== props.workflowId)
        .map((workflow) => ({ value: workflow.id, text: `${workflow.name} (${workflow.owner})` })),
);

const versionOptions = computed(() =>
    versions.value.map((version, index) => {
        const markers = index === versions.value.length - 1 ? ["newest"] : [];
        return { value: String(version.version), text: workflowVersionText(version, markers) };
    }),
);

const helpText = computed(() => {
    if (source.value === "galaxy") {
        return `The step runs the chosen version instead of its current sub-workflow. ${CONNECTIONS_HELP} Another user's workflow is copied into your account, and the step uses the copy.`;
    }
    if (source.value === "trs") {
        return `The step runs the chosen TRS version instead of its current sub-workflow. ${CONNECTIONS_HELP} ${IMPORT_HELP}`;
    }
    return `Enter a link to a workflow file, e.g. a file on GitHub, or the URL of a version on a TRS server. ${CONNECTIONS_HELP} ${IMPORT_HELP}`;
});

const target = computed(() => {
    if (source.value === "trs") {
        return trsTarget.value;
    }
    if (source.value === "url") {
        const trimmedUrl = url.value.trim();
        return trimmedUrl ? { url: trimmedUrl } : null;
    }
    if (!selectedWorkflowId.value || selectedVersion.value === null) {
        return null;
    }
    return { stored_workflow_id: selectedWorkflowId.value, version: parseInt(selectedVersion.value, 10) };
});

let searchCount = 0;

async function search(text: string) {
    const current = ++searchCount;
    loading.value = true;
    error.value = null;
    try {
        const { data } = await loadWorkflows({
            sortBy: "update_time",
            sortDesc: true,
            limit: 50,
            offset: 0,
            filterText: text,
            showPublished: true,
            showShared: true,
            skipStepCounts: true,
        });
        if (current === searchCount) {
            workflows.value = data;
        }
    } catch (e) {
        if (current === searchCount) {
            error.value = errorMessageAsString(e);
        }
    } finally {
        if (current === searchCount) {
            loading.value = false;
        }
    }
}

const searchAfterTyping = useDebounceFn(search, SEARCH_DELAY_MS);

watch([expanded, source], () => {
    if (expanded.value && source.value === "galaxy") {
        search("");
    }
});

watch(source, () => {
    trsTarget.value = null;
    error.value = null;
});

watch(selectedWorkflowId, async (workflowId) => {
    versions.value = [];
    selectedVersion.value = null;
    error.value = null;
    if (!workflowId) {
        return;
    }
    try {
        const loaded: WorkflowVersion[] = await getVersions(workflowId);
        if (workflowId === selectedWorkflowId.value) {
            versions.value = loaded;
            const newest = loaded[loaded.length - 1];
            selectedVersion.value = newest ? String(newest.version) : null;
        }
    } catch (e) {
        if (workflowId === selectedWorkflowId.value) {
            error.value = errorMessageAsString(e);
        }
    }
});

function onReplace() {
    if (!target.value) {
        return;
    }
    emit("onAttemptRefactor", [
        {
            action_type: "upgrade_subworkflow",
            step: { order_index: props.stepId },
            recursive: false,
            ...target.value,
        },
    ]);
}
</script>

<template>
    <div class="ui-form-element section-row" data-description="subworkflow replace">
        <GButton
            size="small"
            color="blue"
            outline
            :aria-expanded="expanded ? 'true' : 'false'"
            @click="expanded = !expanded">
            Replace with another workflow
        </GButton>
        <template v-if="expanded">
            <GSelect v-model="source" size="small" class="mt-1" aria-label="Replacement source">
                <option value="galaxy">Workflow in Galaxy</option>
                <option value="trs">TRS server, e.g. Dockstore</option>
                <option value="url">URL, e.g. GitHub</option>
            </GSelect>
            <template v-if="source === 'galaxy'">
                <Multiselect
                    v-model="selectedWorkflow"
                    class="mt-1"
                    name="replacement-workflow"
                    label="text"
                    track-by="value"
                    placeholder="Search your, shared and published workflows"
                    deselect-label=""
                    select-label=""
                    selected-label=""
                    :allow-empty="false"
                    :internal-search="false"
                    :loading="loading"
                    :options="workflowOptions"
                    @search-change="searchAfterTyping">
                    <template v-slot:noOptions>No workflows found.</template>
                    <template v-slot:noResult>No workflows found.</template>
                </Multiselect>
                <GSelect
                    v-if="versionOptions.length"
                    v-model="selectedVersion"
                    size="small"
                    class="mt-1"
                    aria-label="Version of the replacement workflow">
                    <option v-for="option in versionOptions" :key="option.value" :value="option.value">
                        {{ option.text }}
                    </option>
                </GSelect>
            </template>
            <FormSubworkflowReplaceTrs v-else-if="source === 'trs'" @target="trsTarget = $event" />
            <GFormInput
                v-else
                v-model="url"
                class="mt-1"
                size="small"
                type="url"
                aria-label="URL of the replacement workflow"
                placeholder="https://github.com/org/repo/blob/main/workflow.ga" />
            <div v-if="error" class="text-danger">{{ error }}</div>
            <div class="ui-form-info form-text text-muted">{{ helpText }}</div>
            <GButton size="small" class="mt-1" :disabled="!target" @click="onReplace">Replace</GButton>
        </template>
    </div>
</template>
