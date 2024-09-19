<script setup lang="ts">
import { BModal } from "bootstrap-vue";
import { computed, ref } from "vue";

import { type InvocationExportPlugin } from "@/components/Workflow/Invocation/Export/Plugins";

import ExportForm from "@/components/Common/ExportForm.vue";

const modal = ref<BModal>();

interface Props {
    exportPlugin: InvocationExportPlugin;
    invocationId: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "onExportToFileSource", exportDirectory: string, fileName: string): void;
}>();

const title = computed(() => `Export ${props.exportPlugin.title} to remote file source`);

/** Opens the modal dialog. */
function showModal() {
    modal.value?.show();
}

/** Closes the modal dialog. */
function hideModal() {
    modal.value?.hide();
}

function doExport(exportDirectory: string, fileName: string) {
    emit("onExportToFileSource", exportDirectory, fileName);
}

defineExpose({ showModal, hideModal });
</script>

<template>
    <BModal ref="modal" :title="title" title-tag="h2" centered hide-footer>
        <ExportForm what="workflow invocation" @export="doExport" />
    </BModal>
</template>
