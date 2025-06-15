<script setup lang="ts">
import { faUpload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BCard, BCardTitle, BLink } from "bootstrap-vue";

import { useWorkbookDropHandling } from "@/components/Collections/common/useWorkbooks";

async function handleWorkbook(base64Content: string) {
    emit("workbookContents", base64Content);
}

const {
    browseFiles,
    dropZoneClasses,
    handleDrop,
    HiddenWorkbookUploadInput,
    isDragging,
    onFileUpload,
    uploadErrorMessage,
    uploadRef,
} = useWorkbookDropHandling(handleWorkbook);

const emit = defineEmits(["workbookContents"]);
</script>
<template>
    <BCard
        data-galaxy-file-drop-target
        :class="dropZoneClasses"
        @drop.prevent="handleDrop"
        @dragover.prevent="isDragging = true"
        @dragleave.prevent="isDragging = false">
        <BCardTitle>
            <b>Step 3: Upload</b>
        </BCardTitle>
        <div v-if="uploadErrorMessage">
            <BAlert variant="danger" show>
                {{ uploadErrorMessage }}
            </BAlert>
        </div>
        <div>
            <BLink href="#" @click.prevent="browseFiles">
                <FontAwesomeIcon size="xl" :icon="faUpload" />
                Drop completed workbook here or click to upload.
            </BLink>
            <HiddenWorkbookUploadInput ref="uploadRef" @onFileUpload="onFileUpload" />
        </div>
    </BCard>
</template>

<style scoped>
@import "theme/blue.scss";
@import "@/components/Collections/wizard/workbook-dropzones.scss";

.dropzone {
    padding: 7px !important;
    width: 100%;
}
</style>
