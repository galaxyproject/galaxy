<script setup lang="ts">
import { ref, watch } from "vue";
import { useRouter } from "vue-router/composables";

import { getQueryValue } from "@/utils/route";
import { urlData } from "@/utils/url";

import NewEditor from "@/components/Workflow/Editor/NewEditor.vue";

const router = useRouter();

const emit = defineEmits<{
    (e: "update:confirmation", confirmation: boolean): void;
}>();

const storedWorkflowId = ref<string | undefined>();
const workflowId = ref<string | undefined>();
const version = ref<number | undefined>();
const skipNextReload = ref(false);
const editorReloadKey = ref(0);
const editorConfig = ref<{
    id: string;
    dataManagers: any[];
    initialVersion: number;
    moduleSections: any[];
    tags: any[];
    workflows: any[];
}>();

async function getEditorConfig() {
    let reloadEditor = true;

    if (skipNextReload.value) {
        reloadEditor = false;
        skipNextReload.value = false;
    }

    storedWorkflowId.value = getQueryValue("id");
    workflowId.value = getQueryValue("workflow_id");
    version.value = parseInt(getQueryValue("version") || "", 10);

    const params: {
        id?: string;
        version?: string;
        workflow_id?: string;
    } = {};

    if (workflowId.value) {
        params.workflow_id = workflowId.value.toString();
    } else if (storedWorkflowId.value) {
        params.id = storedWorkflowId.value.toString();
    }
    if (version.value) {
        params.version = version.value.toString();
    }

    editorConfig.value = await urlData({ url: "/workflow/editor", params });

    if (reloadEditor) {
        editorReloadKey.value += 1;
    }
}

watch(
    () => router.currentRoute.query,
    () => {
        getEditorConfig();
    },
    { immediate: true }
);
</script>

<template>
    <NewEditor
        v-if="editorConfig"
        :key="editorReloadKey"
        :workflow-id="editorConfig.id"
        :data-managers="editorConfig.dataManagers"
        :initial-version="editorConfig.initialVersion"
        :module-sections="editorConfig.moduleSections"
        :workflow-tags="editorConfig.tags"
        @update:confirmation="emit('update:confirmation', $event)"
        @skipNextReload="() => (skipNextReload = true)" />
</template>
