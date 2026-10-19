<script setup lang="ts">
import { faUpload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BCard, BCardTitle } from "bootstrap-vue";

import { useWorkbookDropHandling } from "@/components/Collections/common/useWorkbooks";

import GAlert from "@/components/BaseComponents/GAlert.vue";
import GLink from "@/components/BaseComponents/GLink.vue";

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
            <GAlert variant="danger" show>
                {{ uploadErrorMessage }}
            </GAlert>
        </div>
        <div>
            <GLink @click="browseFiles">
                <FontAwesomeIcon size="xl" :icon="faUpload" />
                Drop completed workbook here or click to upload.
            </GLink>
            <HiddenWorkbookUploadInput
                ref="uploadRef"
                data-description="workbook card file input"
                @onFileUpload="onFileUpload" />
        </div>
    </BCard>
</template>

<style lang="scss" scoped>
@import "@/style/scss/theme/blue.scss";
@import "@/components/Collections/wizard/workbook-dropzones.scss";

.dropzone {
    padding: 7px !important;
    width: 100%;
}
</style>
