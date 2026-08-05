<!-- Global generic file upload modal.

    This modal will be suppressed if page has any DOM elements decorated
    with data-galaxy-file-drop-target - see fileDrop composable for more information.
-->
<script setup lang="ts">
import { computed, ref, watch } from "vue";

import { setIframeEvents } from "@/components/Upload/utils";
import { useFileDrop } from "@/composables/fileDrop";
import { useToast } from "@/composables/toast";
import { useUploadMethodModal } from "@/composables/upload/useUploadMethodModal";

const dialog = ref<HTMLDialogElement | null>(null);
const modalContentElement = ref(null);
const { isFileOverDocument, isFileOverDropZone } = useFileDrop({
    dropZone: modalContentElement,
    onDrop,
    onDropCancel,
    solo: true,
});

const modalClass = computed(() => {
    if (isFileOverDropZone.value) {
        return "ui-drag-and-drop-modal drag-over";
    } else {
        return "ui-drag-and-drop-modal";
    }
});

const { openUploadModal } = useUploadMethodModal();

const toast = useToast();

const iframesNoInteract = ["galaxy_main", "frame.center-frame"];

function onDrop(event: DragEvent) {
    console.debug(event.dataTransfer);

    if (event.dataTransfer?.files?.length) {
        void openUploadModal({
            allowedMethods: ["local-file"],
            hideTips: true,
            immediateFiles: Array.from(event.dataTransfer.files),
        });
    }
}

function onDialogClose() {
    isFileOverDocument.value = false;
}

function onDropCancel(event: DragEvent) {
    if (event.dataTransfer?.files?.length) {
        toast.error("Upload cancelled", "Drop file in the center to upload it");
    }
}

watch(isFileOverDocument, (newValue, oldValue) => {
    if (newValue) {
        dialog.value?.showModal();
    } else {
        dialog.value?.close();
    }

    if (!oldValue && newValue) {
        setIframeEvents(iframesNoInteract, true);
    } else {
        setIframeEvents(iframesNoInteract, false);
    }
});
</script>

<template>
    <dialog ref="dialog" :class="modalClass" @close="onDialogClose">
        <div ref="modalContentElement" class="inner-content h-xl">Drop Files here to Upload</div>
    </dialog>
</template>

<style lang="scss">
@import "@/style/scss/theme/blue.scss";

.ui-drag-and-drop-modal {
    width: 100%;
    max-width: 85%;

    background-color: transparent;
    border-radius: 16px;
    border: 6px dashed;
    border-color: $brand-secondary;
    min-height: 80vh;
    padding: 0;

    &[open] {
        display: flex;
    }

    &::backdrop {
        background-color: rgba(0, 0, 0, 0.5);
    }

    .inner-content {
        flex: 1 1 auto;
        display: grid;
        place-items: center;
        color: $brand-secondary;
        font-weight: bold;
    }

    &.drag-over {
        border-color: lighten($brand-info, 30%);
        background-color: rgba(darken($brand-info, 20%), 0.4);

        .inner-content {
            color: lighten($brand-info, 30%);
        }
    }
}
</style>
