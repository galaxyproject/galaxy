<script setup>
import { useFileDrop } from "composables/fileDrop";
import { useGlobalUploadModal } from "composables/globalUploadModal";
import { computed, ref } from "vue";
import { useToast } from "@/composables/toast";

const modalContentElement = ref(null);
const { isFileOverDocument, isFileOverDropZone } = useFileDrop(modalContentElement, onDrop, onDropCancel, true);

const modalClass = computed(() => {
    if (isFileOverDropZone.value) {
        return "ui-drag-and-drop-modal drag-over";
    } else {
        return "ui-drag-and-drop-modal";
    }
});

const { openGlobalUploadModal } = useGlobalUploadModal();

const toast = useToast();

function onDrop(event) {
    console.debug(event.dataTransfer);

    if (event.dataTransfer?.files?.length > 0) {
        openGlobalUploadModal({
            immediateUpload: true,
            immediateFiles: event.dataTransfer.files,
        });
    }
}

function onDropCancel(event) {
    if (event.dataTransfer?.files?.length > 0) {
        toast.error("Please try again", "Upload cancelled");
    }
}
</script>

<template>
    <BModal v-model="isFileOverDocument" :modal-class="modalClass" hide-header hide-footer centered>
        <div ref="modalContentElement" class="inner-content h-xl">Drop Files here to Upload</div>
    </BModal>
</template>

<style lang="scss">
@import "theme/blue.scss";

.ui-drag-and-drop-modal {
    .modal-dialog {
        width: 100%;
        max-width: 85%;
    }

    .modal-content {
        background-color: transparent;
        border-radius: 16px;
        border: 6px dashed;
        border-color: $brand-secondary;
        min-height: 80vh;

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
            background-color: rgba(darken($brand-info, 20%), 0.4);

            .inner-content {
                color: lighten($brand-info, 30%);
            }
        }
    }
}
</style>
