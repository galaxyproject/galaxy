<script setup lang="ts">
import { faArrowLeft, faSpinner, faUndo } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { computed } from "vue";

import type { HistoryNotebookRevisionDetails } from "@/api/historyNotebooks";

import Markdown from "@/components/Markdown/Markdown.vue";

const props = defineProps<{
    revision: HistoryNotebookRevisionDetails;
    isReverting: boolean;
}>();

const emit = defineEmits<{
    (e: "back"): void;
    (e: "restore", revisionId: string): void;
}>();

const markdownConfig = computed(() => ({
    id: props.revision.id,
    title: `Revision Preview`,
    content: props.revision.content || "",
    model_class: "HistoryNotebook",
    update_time: props.revision.update_time,
}));
</script>

<template>
    <div class="notebook-revision-view d-flex flex-column h-100" data-description="notebook revision view">
        <div class="revision-view-toolbar d-flex align-items-center p-2 border-bottom">
            <BButton variant="link" size="sm" data-description="revision back button" @click="emit('back')">
                <FontAwesomeIcon :icon="faArrowLeft" />
                Back to revisions
            </BButton>
            <span class="flex-grow-1"></span>
            <BButton
                variant="primary"
                size="sm"
                data-description="revision restore button"
                :disabled="isReverting"
                @click="emit('restore', revision.id)">
                <FontAwesomeIcon :icon="isReverting ? faSpinner : faUndo" :spin="isReverting" />
                Restore this version
            </BButton>
        </div>
        <div class="revision-view-content overflow-auto flex-grow-1">
            <Markdown :markdown-config="markdownConfig" :read-only="true" download-endpoint="" />
        </div>
    </div>
</template>

<style scoped>
.revision-view-toolbar {
    background: var(--panel-header-bg);
}
</style>
