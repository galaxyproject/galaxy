<script setup>
import { BModal } from "bootstrap-vue";
import ExportForm from "components/Common/ExportForm";
import { computed, ref } from "vue";

import { InvocationExportPlugin } from "./model";

const modal = ref(null);

const props = defineProps({
    exportPlugin: { type: InvocationExportPlugin, required: true },
    invocationId: { type: String, required: true },
});

const emit = defineEmits(["onExportToFileSource"]);

const title = computed(() => `Export ${props.exportPlugin.title} to remote file source`);

/** Opens the modal dialog. */
function showModal() {
    modal.value.show();
}

/** Closes the modal dialog. */
function hideModal() {
    modal.value.hide();
}

function doExport(exportDirectory, fileName) {
    emit("onExportToFileSource", exportDirectory, fileName);
}

defineExpose({ showModal, hideModal });
</script>

<template>
    <BModal ref="modal" :title="title" title-tag="h2" centered hide-footer>
        <ExportForm what="workflow invocation" @export="doExport" />
    </BModal>
</template>
