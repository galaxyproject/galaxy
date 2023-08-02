<script setup>
import axios from "axios";
import { BButton } from "bootstrap-vue";
import { getAppRoot } from "onload";
import { filesDialog } from "utils/data";
import { UploadQueue } from "utils/uploadbox";
import Vue, { computed, ref } from "vue";

import { defaultNewFileName, uploadModelsToPayload } from "./helpers";
import { defaultModel } from "./model.js";
import { findExtension, hasBrowserSupport, openFileDialog } from "./utils";

import DefaultRow from "./DefaultRow.vue";
import UploadBox from "./UploadBox.vue";
import UploadExtensionDetails from "./UploadExtensionDetails.vue";
import UploadSettingsSelect from "./UploadSettingsSelect.vue";

const props = defineProps({
    multiple: {
        type: Boolean,
        default: true,
    },
    lazyLoadMax: {
        type: Number,
        default: null,
    },
    selectable: {
        type: Boolean,
        default: false,
    },
    hasCallback: {
        type: Boolean,
        default: false,
    },
    details: {
        type: Object,
        required: true,
    },
});

const counterAnnounce = ref(0);
const counterError = ref(0);
const counterRunning = ref(0);
const counterSuccess = ref(0);
const extension = ref(props.details.defaultExtension);
const genome = ref(props.details.defaultDbKey);
const highlightBox = ref(false);
const running = ref(false);
const uploadCompleted = ref(0);
const uploadList = ref({});
const uploadSize = ref(0);

const showHelper = computed(() => Object.keys(uploadList.value).length === 0);
const listExtensions = computed(() => props.details.effectiveExtensions.filter((ext) => !ext.composite_files));
const historyId = computed(() => props.details.history_id);
const counterNonRunning = computed(() => counterAnnounce.value + counterSuccess.value + counterError.value);
const enableReset = computed(() => counterRunning.value == 0 && counterNonRunning.value > 0);
const enableStart = computed(() => counterRunning.value == 0 && counterAnnounce.value > 0);
const enableSources = computed(() => counterRunning.value == 0 && (props.multiple || counterNonRunning.value == 0));
const topInfo = computed(() => {
    let message = "";
    if (counterAnnounce.value == 0) {
        if (hasBrowserSupport) {
            message = "&nbsp;";
        } else {
            message =
                "Browser does not support Drag & Drop. Try Firefox 4+, Chrome 7+, IE 10+, Opera 12+ or Safari 6+.";
        }
    } else {
        if (counterRunning.value == 0) {
            message = `You added ${counterAnnounce.value} file(s) to the queue. Add more files or click 'Start' to proceed.`;
        } else {
            message = `Please wait...${counterAnnounce.value} out of ${counterRunning.value} remaining.`;
        }
    }
    return message;
});

const queue = new UploadQueue({
    historyId: historyId.value,
    get: (index) => uploadList.value[index],
    multiple: props.multiple,
    announce: _eventAnnounce,
    progress: _eventProgress,
    success: _eventSuccess,
    error: _eventError,
    warning: _eventWarning,
    complete: _eventComplete,
    chunkSize: props.details.chunkUploadSize,
});

/** Add files to queue */
function addFiles(files) {
    files.forEach((file) => {
        file.chunk_mode = true;
    });
    queue.add(files);
}

/** Update model */
function _eventInput(index, newData) {
    const it = uploadList.value[index];
    Object.entries(newData).forEach(([key, value]) => {
        it[key] = value;
    });
}

/** Success */
function _eventSuccess(index) {
    var it = uploadList.value[index];
    it.percentage = 100;
    it.status = "success";
    props.details.model.set("percentage", _uploadPercentage(100, it.file_size));
    uploadCompleted.value += it.file_size * 100;
    counterAnnounce.value--;
    counterSuccess.value++;
}

/** Remove all */
function _eventReset() {
    if (counterRunning.value === 0) {
        counterAnnounce.value = 0;
        counterSuccess.value = 0;
        counterError.value = 0;
        counterRunning.value = 0;
        queue.reset();
        uploadList.value = {};
        extension.value = props.details.defaultExtension;
        genome.value = props.details.defaultDbKey;
        props.details.model.set("percentage", 0);
    }
}

function uploadSelect() {
    openFileDialog(addFiles, true);
}

/** Start upload process */
function _eventStart() {
    if (counterAnnounce.value == 0 || counterRunning.value > 0) {
        return;
    }
    uploadSize.value = 0;
    uploadCompleted.value = 0;
    Object.values(uploadList.value).forEach((model) => {
        if (model.status === "init") {
            model.status = "queued";
            uploadSize.value += model.file_size;
        }
    });
    props.details.model.set({ percentage: 0, status: "success" });
    counterRunning.value = counterAnnounce.value;

    // package ftp files separately, and remove them from queue
    _uploadFtp();
    queue.start();
}

/** Package and upload ftp files in a single request */
function _uploadFtp() {
    const list = [];
    Object.values(uploadList.value).forEach((model) => {
        if (model.status === "queued" && model.file_mode === "ftp") {
            queue.remove(model.id);
            list.push(model);
        }
    });
    if (list.length > 0) {
        const data = uploadModelsToPayload(list, historyId.value);
        axios
            .post(`${getAppRoot()}api/tools/fetch`, data)
            .then((message) => {
                list.forEach((model) => {
                    _eventSuccess(model.id, message);
                });
            })
            .catch((message) => {
                list.forEach((model) => {
                    _eventError(model.id, message);
                });
            });
    }
}

/** Progress */
function _eventProgress(index, percentage) {
    const it = uploadList.value[index];
    it.percentage = percentage;
    props.details.model.set("percentage", _uploadPercentage(percentage, it.file_size));
}

/** Calculate percentage of all queued uploads */
function _uploadPercentage(percentage, size) {
    return (uploadCompleted.value + percentage * size) / uploadSize.value;
}

/** A new file has been dropped/selected through the uploadbox plugin */
function _eventAnnounce(index, file) {
    counterAnnounce.value++;
    const uploadModel = {
        ...defaultModel,
        id: index,
        file_name: file.name,
        file_size: file.size,
        file_mode: file.mode || "local",
        file_path: file.path,
        file_uri: file.uri,
        file_data: file,
    };
    Vue.set(uploadList.value, index, uploadModel);
}

/** Error */
function _eventError(index, message) {
    var it = uploadList.value[index];
    it.percentage = 100;
    it.status = "error";
    it.info = message;
    props.details.model.set({
        percentage: _uploadPercentage(100, it.file_size),
        status: "danger",
    });
    uploadCompleted.value += it.file_size * 100;
    counterAnnounce.value--;
    counterError.value++;
}

/** Queue is done */
function _eventComplete() {
    Object.values(uploadList.value).forEach((model) => {
        if (model.status === "queued") {
            model.status = "init";
        }
    });
    counterRunning.value = 0;
}

/** Remove model from upload list */
function _eventRemove(index) {
    const it = uploadList.value[index];
    var status = it.status;
    if (status == "success") {
        counterSuccess.value--;
    } else if (status == "error") {
        counterError.value--;
    } else {
        counterAnnounce.value--;
    }
    Vue.delete(uploadList.value, index);
    queue.remove(index);
}

/** Show remote files dialog or FTP files */
function _eventRemoteFiles() {
    filesDialog(
        (items) => {
            queue.add(
                items.map((item) => {
                    const rval = {
                        mode: "ftp",
                        name: item.label,
                        size: item.size,
                        path: item.url,
                    };
                    return rval;
                })
            );
        },
        { multiple: true }
    );
}

/** Create a new file */
function _eventCreate() {
    queue.add([{ name: defaultNewFileName, size: 0, mode: "new" }]);
}

/** Pause upload process */
function _eventStop() {
    if (counterRunning.value > 0) {
        props.details.model.set("status", "info");
        topInfo.value = "Queue will pause after completing the current file...";
        queue.stop();
    }
}

function _eventWarning(index, message) {
    const it = uploadList.value[index];
    it.status = "warning";
    it.info = message;
}

/* update un-modified default values when globals change */
function updateExtension(newExtension) {
    extension.value = newExtension;
    Object.values(uploadList.value).forEach((model) => {
        if (model.status === "init" && model.extension === props.details.defaultExtension) {
            model.extension = newExtension;
        }
    });
}

function updateGenome(newGenome) {
    Object.values(uploadList.value).forEach((model) => {
        if (model.status === "init" && model.genome === props.details.defaultDbKey) {
            model.genome = newGenome;
        }
    });
}
</script>

<template>
    <div class="upload-view-default">
        <div class="upload-top">
            <div class="upload-top-info" v-html="topInfo" />
        </div>
        <UploadBox :multiple="true" @add="addFiles">
            <div v-show="showHelper" class="upload-helper"><i class="fa fa-files-o" />Drop files here</div>
            <div v-show="!showHelper" class="upload-table ui-table-striped">
                <DefaultRow
                    v-for="(uploadItem, uploadIndex) in uploadList"
                    :key="uploadIndex"
                    :index="uploadIndex"
                    :deferred="uploadItem.deferred"
                    :extension="uploadItem.extension"
                    :file-content="uploadItem.file_content"
                    :file-mode="uploadItem.file_mode"
                    :file-name="uploadItem.file_name"
                    :file-size="uploadItem.file_size"
                    :genome="uploadItem.genome"
                    :list-extensions="listExtensions"
                    :list-genomes="details.listGenomes"
                    :percentage="uploadItem.percentage"
                    :space_to_tab="uploadItem.space_to_tab"
                    :status="uploadItem.status"
                    :to_posix_lines="uploadItem.to_posix_lines"
                    @remove="_eventRemove"
                    @input="_eventInput" />
            </div>
        </UploadBox>
        <div class="upload-footer text-center">
            <span class="upload-footer-title">Type (set all):</span>
            <UploadSettingsSelect
                :value="extension"
                :options="listExtensions"
                placeholder="Select Type"
                :disabled="running"
                @input="updateExtension" />
            <UploadExtensionDetails :extension="extension" :list-extensions="listExtensions" />
            <span class="upload-footer-title">Reference (set all):</span>
            <UploadSettingsSelect
                :value="genome"
                :options="details.listGenomes"
                :disabled="running"
                placeholder="Select Reference"
                @input="updateGenome" />
        </div>
        <div class="upload-buttons d-flex justify-content-end">
            <BButton id="btn-local" title="Choose local files" :disabled="!enableSources" @click="uploadSelect">
                <span class="fa fa-laptop"></span>
                <span v-localize>Choose local files</span>
            </BButton>
            <BButton
                v-if="!details.fileSourcesConfigured || !!details.currentFtp"
                id="btn-remote-files"
                :disabled="!enableSources"
                @click="_eventRemoteFiles">
                <span class="fa fa-folder-open"></span>
                <span v-localize>Choose remote files</span>
            </BButton>
            <BButton id="btn-new" title="Paste/Fetch data" :disabled="!enableSources" @click="_eventCreate">
                <span class="fa fa-edit"></span>
                <span v-localize>Paste/Fetch data</span>
            </BButton>
            <BButton
                id="btn-start"
                :disabled="!enableStart"
                title="Start"
                :variant="enableStart ? 'primary' : ''"
                @click="_eventStart">
                <span v-localize>Start</span>
            </BButton>
            <BButton id="btn-stop" title="Pause" :disabled="counterRunning == 0" @click="_eventStop">
                <span v-localize>Pause</span>
            </BButton>
            <BButton id="btn-reset" title="Reset" :disabled="!enableReset" @click="_eventReset">
                <span v-localize>Reset</span>
            </BButton>
            <BButton id="btn-close" title="Close" @click="$emit('dismiss')">
                <span v-if="hasCallback" v-localize>Cancel</span>
                <span v-else v-localize>Close</span>
            </BButton>
        </div>
    </div>
</template>
