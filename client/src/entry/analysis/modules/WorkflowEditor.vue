<script setup lang="ts">
import { ref, watch } from "vue";
import { useRoute } from "vue-router/composables";

import { getWorkflowInfo } from "@/api/workflows";

import NewEditor from "@/components/Workflow/Editor/Index.vue";

const route = useRoute();

const emit = defineEmits<{
    (e: "update:confirmation", confirmation: boolean): void;
}>();

const storedWorkflowId = ref<string | undefined>();
const workflowId = ref<string | undefined>();
const version = ref<number | undefined>();
const workflowTags = ref<string[]>([]);
const skipNextReload = ref(false);
const newWorkflow = ref(false);
const editorReloadKey = ref(0);

async function getEditorConfig() {
    let reloadEditor = true;

    if (skipNextReload.value) {
        reloadEditor = false;
        skipNextReload.value = false;
    }

    const versionParam = route.query.version as string | undefined;
    version.value = versionParam !== undefined ? parseInt(versionParam, 10) : undefined;
    storedWorkflowId.value = route.query.id as string;
    workflowId.value = route.query.workflow_id as string;

    const workflowIdValue = workflowId.value || storedWorkflowId.value;
    if (!workflowIdValue) {
        newWorkflow.value = true;
        if (reloadEditor) {
            editorReloadKey.value += 1;
        }
        return;
    }
    newWorkflow.value = false;
    if (workflowId.value) {
        const { id: storedWorkflowIdValue, tags } = await getWorkflowInfo(workflowIdValue, version.value, true);
        storedWorkflowId.value = storedWorkflowIdValue;
        workflowTags.value = tags;
    }

    if (reloadEditor) {
        editorReloadKey.value += 1;
    }
}

watch(
    () => route.query,
    () => {
        getEditorConfig();
    },
    { immediate: true, deep: true },
);
</script>

<template>
    <NewEditor
        v-if="storedWorkflowId || newWorkflow"
        :key="editorReloadKey"
        :workflow-id="storedWorkflowId"
        :initial-version="version"
        :workflow-tags="workflowTags"
        @update:confirmation="emit('update:confirmation', $event)"
        @skipNextReload="() => (skipNextReload = true)"
        @forceReload="editorReloadKey += 1" />
</template>
