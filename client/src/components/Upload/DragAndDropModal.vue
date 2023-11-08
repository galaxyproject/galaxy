<script setup>
import { useFileDrop } from "composables/fileDrop";
import { useGlobalUploadModal } from "composables/globalUploadModal";
import { computed, ref } from "vue";

import { Toast } from "@/composables/toast";

const modalContentElement = ref(null);
const { isFileOverDocument, isFileOverDropZone } = useFileDrop(modalContentElement, onDrop, onDropFail, true);

const modalClass = computed(() => {
    if (isFileOverDropZone.value) {
        return "ui-drag-and-drop-modal drag-over";
    } else {
        return "ui-drag-and-drop-modal";
    }
});

const { openGlobalUploadModal } = useGlobalUploadModal();

function onDrop(event) {
    console.debug(event.dataTransfer);

    if (event.dataTransfer?.files?.length > 0) {
        openGlobalUploadModal({
            immediateUpload: true,
            immediateFiles: event.dataTransfer.files,
        });
    }
}

function onDropFail(event) {
    if (event.dataTransfer?.files?.length > 0) {
        Toast.error("Please try again", "File failed");
    }
}
</script>

<template>
    <BModal v-model="isFileOverDocument" :modal-class="modalClass" size="md" hide-header hide-footer centered>
        <div ref="modalContentElement" class="inner-content h-xl">Drop Files here to Upload</div>
    </BModal>
</template>

<style lang="scss">
@import "theme/blue.scss";

.ui-drag-and-drop-modal {
    .modal-content {
        background-color: transparent;
        border-radius: 16px;
        border: 6px dashed;
        border-color: $brand-secondary;
        min-height: 40vh;

        .modal-body {
            display: flex;
        }

        .inner-content {
            flex: 1 1 auto;
            display: grid;
            place-items: center;
            color: $brand-secondary;
            font-weight: bold;
        }
    }

    &.drag-over {
        .modal-content {
            border-color: lighten($brand-info, 30%);
            background-color: rgba($black, 0.3);

            .inner-content {
                color: lighten($brand-info, 30%);
            }
        }
    }
}
</style>
