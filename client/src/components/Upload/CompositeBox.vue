<script setup>
import { BButton } from "bootstrap-vue";
import Vue, { computed, ref } from "vue";

import { uploadPayload } from "@/utils/upload-payload.js";
import { uploadSubmit } from "@/utils/upload-submit.js";

import { defaultModel } from "./model";

import CompositeRow from "./CompositeRow.vue";
import UploadSelect from "./UploadSelect.vue";

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
    listDbKeys: {
        type: Array,
        required: true,
    },
});

const extension = ref(null);
const dbKey = ref(props.defaultDbKey);
const uploadItems = ref({});

const enableStart = computed(() => {
    const incomplete = uploadValues.value.find((v) => v.status === "init" && !v.optional && v.fileSize === 0);
    return !isRunning.value && uploadValues.value.length > 0 && !incomplete;
});

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
    restoreStatus();
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
        dbKey.value = props.defaultDbKey;
    }
}

/** Start upload process */
function eventStart() {
    uploadValues.value.forEach((model) => {
        model.dbKey = dbKey.value;
        model.extension = extension.value;
    });
    try {
        uploadSubmit({
            data: uploadPayload(uploadValues.value, props.historyId, true),
            error: eventError,
            progress: eventProgress,
            success: eventSuccess,
            isComposite: true,
        });
    } catch (e) {
        eventError(String(e));
    }
}

/** Refresh success state */
function eventSuccess() {
    uploadValues.value.forEach((model) => {
        model.percentage = 100;
        model.status = "success";
    });
}

function inputDbkey(newDbkey) {
    dbKey.value = newDbkey;
    restoreStatus();
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
    restoreStatus();
}

/** Refresh init state if any user changes attributes */
function restoreStatus() {
    uploadValues.value.forEach((model) => {
        model.percentage = 0;
        model.status = "init";
    });
}

defineExpose({
    enableStart,
    listExtensions,
    showHelper,
});
</script>

<template>
    <div class="upload-wrapper">
        <div class="upload-header">&nbsp;</div>
        <div class="upload-box">
            <div v-show="showHelper" class="upload-helper">选择一个复合类型</div>
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
                    :optional="uploadItem.optional"
                    :percentage="uploadItem.percentage"
                    :space-to-tab="uploadItem.spaceToTab"
                    :status="uploadItem.status"
                    :to-posix-lines="uploadItem.toPosixLines"
                    @input="eventInput" />
            </div>
        </div>
        <div class="upload-footer">
            <span class="upload-footer-title">复合类型：</span>
            <UploadSelect
                class="upload-footer-extension"
                :value="null"
                :options="listExtensions"
                :disabled="isRunning"
                what="文件类型"
                @input="inputExtension" />
            <span class="upload-footer-title">参考：</span>
            <UploadSelect
                what="参考"
                :value="dbKey"
                :options="listDbKeys"
                :disabled="isRunning"
                @input="inputDbkey" />
        </div>
        <div class="upload-buttons d-flex justify-content-end">
            <BButton
                id="btn-start"
                :disabled="!enableStart"
                title="开始"
                :variant="enableStart ? 'primary' : null"
                @click="eventStart">
                <span v-localize>开始</span>
            </BButton>
            <BButton id="btn-reset" title="重置" @click="eventReset">
                <span v-localize>重置</span>
            </BButton>
            <BButton id="btn-close" title="关闭" @click="$emit('dismiss')">
                <span v-if="hasCallback" v-localize>关闭</span>
                <span v-else v-localize>取消</span>
            </BButton>
        </div>
    </div>
</template>
