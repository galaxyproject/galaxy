<script setup>
import { BButton } from "bootstrap-vue";
import { submitUpload } from "utils/uploadbox";
import Vue, { computed, ref } from "vue";

import { uploadPayload } from "@/utils/uploadpayload.js";

import { defaultModel } from "./model.js";

import CompositeRow from "./CompositeRow.vue";
import UploadSettingsSelect from "./UploadSettingsSelect.vue";

const props = defineProps({
    effectiveExtensions: {
        type: Array,
        required: true,
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
    details: {
        type: Object,
        required: true,
    },
});

const extension = ref(null);
const genome = ref(props.details.defaultDbKey);
const uploadItems = ref({});

const hasRemoteFiles = computed(() => !props.details.fileSourcesConfigured || !!props.details.currentFtp);

const listExtensions = computed(() => {
    const result = props.effectiveExtensions.filter((ext) => ext.composite_files);
    result.unshift({ id: null, text: "Select" });
    return result;
});

const running = computed(() => {
    const model = uploadKeys.value[0];
    return model && model.status === "running";
});

const readyStart = computed(() => {
    const readyStates = uploadValues.value.filter((v) => v.file_size > 0).length;
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
        genome.value = props.details.defaultDbKey;
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
    <div class="upload-view-default">
        <div class="upload-box" :style="{ height: '335px' }">
            <div v-show="showHelper" class="upload-helper">Select a composite type</div>
            <div v-show="!showHelper">
                <CompositeRow
                    v-for="(uploadItem, uploadIndex) in uploadItems"
                    :key="uploadIndex"
                    :index="uploadIndex"
                    :file-description="uploadItem.description"
                    :file-content="uploadItem.file_content"
                    :file-mode="uploadItem.file_mode"
                    :file-name="uploadItem.file_name"
                    :file-size="uploadItem.file_size"
                    :info="uploadItem.info"
                    :has-remote-files="hasRemoteFiles"
                    :percentage="uploadItem.percentage"
                    :space_to_tab="uploadItem.space_to_tab"
                    :status="uploadItem.status"
                    :to_posix_lines="uploadItem.to_posix_lines"
                    @input="eventInput" />
            </div>
        </div>
        <div class="upload-footer">
            <span class="upload-footer-title">Composite Type:</span>
            <UploadSettingsSelect :value="null" :options="listExtensions" :disabled="running" @input="inputExtension" />
            <span class="upload-footer-title">Genome/Build:</span>
            <UploadSettingsSelect :value="genome" :options="listGenomes" :disabled="running" @input="inputDbkey" />
        </div>
        <div class="upload-buttons d-flex justify-content-end">
            <BButton
                id="btn-start"
                :disabled="!readyStart"
                title="Start"
                :variant="readyStart ? 'primary' : ''"
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
