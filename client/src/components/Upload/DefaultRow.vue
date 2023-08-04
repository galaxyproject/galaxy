<script setup>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faEdit, faFolderOpen, faLaptop } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { bytesToString } from "utils/utils";
import { computed, ref } from "vue";

import UploadExtensionDetails from "./UploadExtensionDetails.vue";
import UploadSettings from "./UploadSettings.vue";
import UploadSettingsSelect from "./UploadSettingsSelect.vue";

library.add(faEdit, faLaptop, faFolderOpen);

const props = defineProps({
    deferred: Boolean,
    extension: String,
    fileContent: String,
    fileMode: String,
    fileName: String,
    fileSize: Number,
    genome: String,
    index: String,
    listGenomes: {
        type: Array,
        default: null,
    },
    listExtensions: {
        type: Array,
        default: null,
    },
    percentage: Number,
    space_to_tab: Boolean,
    status: String,
    to_posix_lines: Boolean,
});

const emit = defineEmits();

const percentageInt = computed(() => parseInt(props.percentage || 0));
const removeIcon = computed(() => status_classes[props.status] || status_classes.init);

/** Dictionary of upload states and associated icons */
const status_classes = {
    init: "cursor-pointer fa fa-trash-o",
    queued: "fa fa-spinner fa-spin",
    running: "fa fa-spinner fa-spin",
    success: "cursor-pointer fa fa-check",
    error: "cursor-pointer fa fa-exclamation-triangle",
};

function inputExtension(newExtension) {
    emit("input", props.index, { extension: newExtension });
}

function inputFileContent(newFileContent) {
    emit("input", props.index, { file_content: newFileContent, file_size: newFileContent.length });
}

function inputFileName(newFileName) {
    emit("input", props.index, { file_name: newFileName });
}

function inputGenome(newGenome) {
    emit("input", props.index, { genome: newGenome });
}

function inputSettings(settingId) {
    const newSettings = {};
    newSettings[settingId] = !props[settingId];
    emit("input", props.index, newSettings);
}

function removeUpload() {
    if (["init", "success", "error"].indexOf(props.status) !== -1) {
        emit("remove", props.index);
    }
}
</script>

<template>
    <div :id="`upload-row-${index}`" class="upload-row p-2">
        <div class="d-flex justify-content-around">
            <div>
                <FontAwesomeIcon v-if="fileMode == 'new'" icon="fa-edit" />
                <FontAwesomeIcon v-if="fileMode == 'local'" icon="fa-laptop" />
                <FontAwesomeIcon v-if="fileMode == 'ftp'" icon="fa-folder-open" />
            </div>
            <b-input :value="fileName" class="upload-title p-1 border rounded" @input="inputFileName" />
            <div class="upload-size">
                {{ bytesToString(fileSize) }}
            </div>
            <UploadSettingsSelect
                v-if="listExtensions !== null"
                :value="extension"
                :options="listExtensions"
                placeholder="Select Type"
                @input="inputExtension" />
            <UploadExtensionDetails :extension="extension" :list-extensions="listExtensions" />
            <UploadSettingsSelect
                v-if="listGenomes !== null"
                :value="genome"
                :options="listGenomes"
                placeholder="Select Reference"
                @input="inputGenome" />
            <UploadSettings
                :deferred="deferred"
                :to_posix_lines="to_posix_lines"
                :space_to_tab="space_to_tab"
                @input="inputSettings" />
            <div class="upload-info">
                <div class="upload-info-text" />
                <div class="upload-info-progress progress">
                    <div
                        class="upload-progress-bar progress-bar progress-bar-success"
                        :style="{ width: `${percentageInt}%` }" />
                    <div class="upload-percentage">{{ percentageInt }}%</div>
                </div>
            </div>
            <div>
                <div class="upload-symbol" :class="removeIcon" @click="removeUpload" />
            </div>
        </div>
        <div v-if="fileMode == 'new'" class="upload-text">
            <div class="upload-text-info">
                Download data from the web by entering URLs (one per line) or directly paste content.
            </div>
            <b-textarea :value="fileContent" class="upload-text-content form-control" @input="inputFileContent" />
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";
.upload-text-content {
    width: 100%;
    height: 80px;
    background: inherit;
    color: $text-color;
    white-space: pre;
    overflow: auto;
}
</style>
