<script setup lang="ts">
import { computed, ref, watch } from "vue";

import { loadWorkflows, type RefactorRequestAction, type WorkflowSummary, type WorkflowVersion } from "@/api/workflows";
import { getVersions } from "@/components/Workflow/Editor/modules/services";
import { errorMessageAsString } from "@/utils/simple-error";

import { workflowVersionText } from "./workflowVersionText";

import GButton from "@/components/BaseComponents/GButton.vue";
import GSelect from "@/components/BaseComponents/GSelect.vue";
import DelayedInput from "@/components/Common/DelayedInput.vue";

const props = defineProps<{
    stepId: number;
    /** The stored workflow being edited, which can't be its own step */
    workflowId?: string;
}>();

const emit = defineEmits<{
    (e: "onAttemptRefactor", actions: RefactorRequestAction[]): void;
}>();

const expanded = ref(false);
const filterText = ref("");
const workflows = ref<WorkflowSummary[]>([]);
const loading = ref(false);
const error = ref<string | null>(null);
const selectedWorkflowId = ref<string | null>(null);
const versions = ref<WorkflowVersion[]>([]);
const selectedVersion = ref<string | null>(null);

const workflowOptions = computed(() =>
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
            if (!data.some((workflow) => workflow.id === selectedWorkflowId.value)) {
                selectedWorkflowId.value = null;
            }
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

watch([filterText, expanded], () => {
    if (expanded.value) {
        search(filterText.value);
    }
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
    if (!selectedWorkflowId.value || selectedVersion.value === null) {
        return;
    }
    emit("onAttemptRefactor", [
        {
            action_type: "upgrade_subworkflow",
            step: { order_index: props.stepId },
            stored_workflow_id: selectedWorkflowId.value,
            version: parseInt(selectedVersion.value, 10),
            recursive: false,
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
            <DelayedInput
                v-model="filterText"
                class="mt-1"
                placeholder="search your, shared and published workflows"
                :delay="800"
                :loading="loading" />
            <div v-if="error" class="text-danger">{{ error }}</div>
            <GSelect v-model="selectedWorkflowId" size="small" class="mt-1" aria-label="Replacement workflow">
                <option :value="null" disabled>Select a workflow</option>
                <option v-for="option in workflowOptions" :key="option.value" :value="option.value">
                    {{ option.text }}
                </option>
            </GSelect>
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
            <div class="ui-form-info form-text text-muted">
                The step runs the chosen version instead of its current sub-workflow. Connections stay on inputs and
                outputs with the same names. Another user's workflow is copied into your account, and the step uses the
                copy.
            </div>
            <GButton
                size="small"
                class="mt-1"
                :disabled="!selectedWorkflowId || selectedVersion === null"
                @click="onReplace">
                Replace
            </GButton>
        </template>
    </div>
</template>
