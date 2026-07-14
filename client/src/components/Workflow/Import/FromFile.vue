<script setup lang="ts">
import { faCloudUploadAlt } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import axios from "axios";
import { BForm, BFormFile, BFormGroup } from "bootstrap-vue";
import { computed, type Ref, ref, watch } from "vue";
import { useRouter } from "vue-router/composables";

import { getRedirectOnImportPath } from "@/components/Workflow/redirectPath";
import { useFileDrop } from "@/composables/fileDrop";
import { withPrefix } from "@/utils/redirect";
import { errorMessageAsString } from "@/utils/simple-error";

import { validateWorkflowFile, WORKFLOW_FILE_ACCEPT } from "./workflowValidation";

import GAlert from "@/components/BaseComponents/GAlert.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    /** A file dropped on the parent's method card, to be consumed on mount */
    droppedFile?: File | null;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "input-valid", valid: boolean): void;
}>();

const loading = ref(false);
const sourceFile: Ref<File | null> = ref(null);
const errorMessage: Ref<string | null> = ref(null);
const dropZoneRef = ref<HTMLElement | null>(null);
const fileSetViaDrop = ref(false);

const hasErrorMessage = computed(() => errorMessage.value != null);

// Validation state for wizard mode
const isValid = computed(() => sourceFile.value !== null);

watch(isValid, (newValue) => {
    emit("input-valid", newValue);
});

// Consume a file dropped on the parent's method card
if (props.droppedFile) {
    sourceFile.value = props.droppedFile;
    fileSetViaDrop.value = true;
}

// Drop zone handling
async function onDrop(evt: DragEvent) {
    if (evt.dataTransfer?.files?.length) {
        const file = evt.dataTransfer.files[0];
        if (!file) {
            return;
        }
        const result = await validateWorkflowFile(file, { checkContent: true });
        if (result.valid) {
            sourceFile.value = file;
            fileSetViaDrop.value = true;
        } else {
            errorMessage.value = result.error ?? "Invalid workflow file.";
        }
    }
}

const { isFileOverDropZone } = useFileDrop({
    dropZone: dropZoneRef,
    onDrop,
    onDropCancel: () => {},
    solo: false,
    idleTime: 10000,
    ignoreChildrenOnLeave: true,
});

/** When the user selects a file via the native input, validate it */
async function onFileInput(file: File | null) {
    if (!file) {
        sourceFile.value = null;
        fileSetViaDrop.value = false;
        return;
    }
    const result = await validateWorkflowFile(file, { checkContent: true });
    if (result.valid) {
        sourceFile.value = file;
        fileSetViaDrop.value = false;
    } else {
        sourceFile.value = null;
        fileSetViaDrop.value = false;
        errorMessage.value = result.error ?? "Invalid workflow file.";
    }
}

/** Clear the current file and reset to the browse state */
function clearFile() {
    sourceFile.value = null;
    fileSetViaDrop.value = false;
}

const router = useRouter();

async function submit() {
    const formData = new FormData();

    if (sourceFile.value) {
        formData.append("archive_file", sourceFile.value);
    }

    loading.value = true;

    try {
        const response = await axios.post(withPrefix("/api/workflows"), formData);
        const path = getRedirectOnImportPath(response.data);

        router.push(path);
    } catch (error) {
        errorMessage.value = errorMessageAsString(error);
    } finally {
        loading.value = false;
    }
}

// Expose method for wizard submit
async function attemptImport() {
    await submit();
}

defineExpose({ attemptImport });
</script>

<template>
    <BForm class="mt-4 workflow-import-file" @submit.prevent="submit">
        <div
            ref="dropZoneRef"
            class="workflow-drop-zone"
            :class="{ 'workflow-drop-zone-active': isFileOverDropZone }"
            data-galaxy-file-drop-target>
            <div v-if="!sourceFile" class="mb-3">
                <FontAwesomeIcon :icon="faCloudUploadAlt" size="3x" class="text-muted" />
                <p class="mt-2 mb-1 font-weight-medium">Drag a workflow file here</p>
                <p class="text-muted small mb-2">or</p>
            </div>
            <BFormGroup :label="sourceFile ? 'Workflow File' : 'Browse for a file'">
                <!-- When a file was set via drop, the native file input can't reflect
                     it programmatically, so we show the filename manually instead. -->
                <div v-if="fileSetViaDrop && sourceFile" class="text-center py-2">
                    <span class="font-weight-bold text-break">{{ sourceFile.name }}</span>
                    <div class="mt-1">
                        <GButton transparent size="small" @click="clearFile">Choose another</GButton>
                    </div>
                </div>
                <BFormFile
                    v-show="!fileSetViaDrop"
                    v-model="sourceFile"
                    :accept="WORKFLOW_FILE_ACCEPT"
                    @input="onFileInput" />
                <span v-if="!sourceFile" class="text-muted small">
                    Accepted formats: <code>*.ga</code>, <code>*.yml</code>, <code>*.yaml</code>
                </span>
            </BFormGroup>
        </div>

        <GAlert :show="hasErrorMessage" variant="danger">
            {{ errorMessage }}
        </GAlert>

        <GAlert v-if="loading" variant="info">
            <LoadingSpan message="Loading your workflow, this may take a while - please be patient." />
        </GAlert>
    </BForm>
</template>

<style scoped lang="scss">
@import "@/style/scss/theme/blue.scss";

.workflow-drop-zone {
    border: 2px dashed $border-color;
    border-radius: $border-radius-large;
    text-align: center;
    background-color: $gray-100;
    padding: 1.5rem;
    margin-bottom: 1rem;
    transition:
        border-color 0.3s ease,
        background-color 0.3s ease;

    &.workflow-drop-zone-active {
        border-color: $brand-primary;
        background-color: lighten($brand-primary, 60%);
    }
}
</style>
