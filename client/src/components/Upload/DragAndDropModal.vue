<script setup>
import { ref, computed } from "vue";
import { useFileDrop } from "composables/fileDrop";
import { useGlobalUploadModal } from "composables/globalUploadModal";

const modalContentElement = ref(null);
const { isFileOverDocument, isFileOverDropZone } = useFileDrop(modalContentElement, onDrop, true);

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
</script>

<template>
    <b-modal v-model="isFileOverDocument" :modal-class="modalClass" hide-header hide-footer centered>
        <div ref="modalContentElement" class="inner-content h-xl">Drop Files here to Upload</div>
    </b-modal>
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

            .inner-content {
                color: lighten($brand-info, 30%);
            }
        }
    }
}
</style>
