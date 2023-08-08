<script setup>
import { BButton } from "bootstrap-vue";
import { submitUpload } from "utils/uploadbox";
import Vue, { computed, ref } from "vue";

import { uploadPayload } from "@/utils/uploadpayload.js";

import { defaultModel } from "./model.js";

import CompositeRow from "./CompositeRow.vue";
import UploadSettingsSelect from "./UploadSettingsSelect.vue";

const props = defineProps({
    defaultDbKey: {
        type: String,
        required: true,
    },
    effectiveExtensions: {
        type: Array,
        required: true,
    },
    fileSourcesConfigured: {
        type: Boolean,
        required: true,
    },
    ftpUploadSite: {
        type: String,
        default: null,
    },
    hasCallback: {
        type: Boolean,
        default: false,
    },
    historyId: {
        type: String,
        default: null,
    },
    listGenomes: {
        type: Array,
        required: true,
    },
});

const extension = ref(null);
const genome = ref(props.defaultDbKey);
const uploadItems = ref({});

const hasRemoteFiles = computed(() => props.fileSourcesConfigured || !!props.ftpUploadSite);

const isRunning = computed(() => {
    const model = uploadKeys.value[0];
    return model && model.status === "running";
});

const listExtensions = computed(() => {
    const result = props.effectiveExtensions.filter((ext) => ext.composite_files);
    result.unshift({ id: null, text: "Select" });
    return result;
});

const readyStart = computed(() => {
    const readyStates = uploadValues.value.filter((v) => v.fileSize > 0).length;
    const optionalStates = uploadValues.value.filter((v) => v.optional === true).length;
    return readyStates + optionalStates == uploadValues.value.length && uploadValues.value.length > 0;
});

const showHelper = computed(() => uploadKeys.value.length === 0);
const uploadValues = computed(() => Object.values(uploadItems.value));
const uploadKeys = computed(() => Object.keys(uploadItems.value));

/** Refresh error state */
function eventError(message) {
    uploadValues.value.forEach((model) => {
        model.info = message;
        model.status = "error";
    });
}

/** Update model */
function eventInput(index, newData) {
    const it = uploadItems.value[index];
    Object.entries(newData).forEach(([key, value]) => {
        it[key] = value;
    });
}

/** Refresh progress state */
function eventProgress(percentage) {
    uploadValues.value.forEach((model) => {
        model.percentage = percentage;
    });
}

/** Remove all */
function eventReset() {
    if (!uploadValues.value.find((v) => v.status === "running")) {
        uploadItems.value = {};
        genome.value = props.defaultDbKey;
    }
}

/** Start upload process */
function eventStart() {
    uploadValues.value.forEach((model) => {
        model.genome = genome.value;
        model.extension = extension.value;
    });
    submitUpload({
        data: uploadPayload(uploadValues.value, props.historyId, true),
        error: eventError,
        progress: eventProgress,
        success: eventSuccess,
        isComposite: true,
    });
}

/** Refresh success state */
function eventSuccess() {
    uploadValues.value.forEach((model) => {
        model.percentage = 100;
        model.status = "success";
    });
}

function inputDbkey(newDbkey) {
    genome.value = newDbkey;
}

function inputExtension(newExtension) {
    extension.value = newExtension;
    uploadItems.value = {};
    let uploadCount = 0;
    const extensionDetails = listExtensions.value.find((v) => v.id === newExtension);
    if (extensionDetails && extensionDetails.composite_files) {
        extensionDetails.composite_files.forEach((item) => {
            const index = String(uploadCount++);
            const uploadModel = {
                ...defaultModel,
                description: item.description || item.name,
                optional: item.optional,
            };
            Vue.set(uploadItems.value, index, uploadModel);
        });
    }
}
</script>

<template>
    <div class="upload-wrapper">
        <div class="upload-header">&nbsp;</div>
        <div class="upload-box">
            <div v-show="showHelper" class="upload-helper">Select a composite type</div>
            <div v-show="!showHelper">
                <CompositeRow
                    v-for="(uploadItem, uploadIndex) in uploadItems"
                    :key="uploadIndex"
                    :index="uploadIndex"
                    :file-description="uploadItem.description"
                    :file-content="uploadItem.fileContent"
                    :file-mode="uploadItem.fileMode"
                    :file-name="uploadItem.fileName"
                    :file-size="uploadItem.fileSize"
                    :info="uploadItem.info"
                    :has-remote-files="hasRemoteFiles"
                    :percentage="uploadItem.percentage"
                    :space-to-tab="uploadItem.spaceToTab"
                    :status="uploadItem.status"
                    :to-posix-lines="uploadItem.toPosixLines"
                    @input="eventInput" />
            </div>
        </div>
        <div class="upload-footer">
            <span class="upload-footer-title">Composite Type:</span>
            <UploadSettingsSelect
                :value="null"
                :options="listExtensions"
                :disabled="isRunning"
                @input="inputExtension" />
            <span class="upload-footer-title">Genome/Build:</span>
            <UploadSettingsSelect :value="genome" :options="listGenomes" :disabled="isRunning" @input="inputDbkey" />
        </div>
        <div class="upload-buttons d-flex justify-content-end">
            <BButton
                id="btn-start"
                :disabled="!readyStart"
                title="Start"
                :variant="readyStart ? 'primary' : null"
                @click="eventStart">
                <span v-localize>Start</span>
            </BButton>
            <BButton id="btn-reset" title="Reset" @click="eventReset">
                <span v-localize>Reset</span>
            </BButton>
            <BButton title="Close" @click="$emit('dismiss')">
                <span v-if="hasCallback" v-localize>Close</span>
                <span v-else v-localize>Cancel</span>
            </BButton>
        </div>
    </div>
</template>
