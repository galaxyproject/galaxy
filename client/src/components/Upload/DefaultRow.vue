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
    info: String,
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
const isDisabled = computed(() => props.status !== "init");
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
    <div :id="`upload-row-${index}`" class="upload-row rounded my-1 p-2" :class="`upload-${status}`">
        <div class="d-flex justify-content-around">
            <div>
                <FontAwesomeIcon v-if="fileMode == 'new'" icon="fa-edit" />
                <FontAwesomeIcon v-if="fileMode == 'local'" icon="fa-laptop" />
                <FontAwesomeIcon v-if="fileMode == 'ftp'" icon="fa-folder-open" />
            </div>
            <b-input
                :value="fileName"
                class="upload-title p-1 border rounded"
                :disabled="isDisabled"
                @input="inputFileName" />
            <div class="upload-size">
                {{ bytesToString(fileSize) }}
            </div>
            <UploadSettingsSelect
                v-if="listExtensions !== null"
                :value="extension"
                :disabled="isDisabled"
                :options="listExtensions"
                placeholder="Select Type"
                @input="inputExtension" />
            <UploadExtensionDetails
                v-if="listExtensions !== null"
                :extension="extension"
                :list-extensions="listExtensions" />
            <UploadSettingsSelect
                v-if="listGenomes !== null"
                :value="genome"
                :disabled="isDisabled"
                :options="listGenomes"
                placeholder="Select Reference"
                @input="inputGenome" />
            <UploadSettings
                :deferred="deferred"
                :disabled="isDisabled"
                :to_posix_lines="to_posix_lines"
                :space_to_tab="space_to_tab"
                @input="inputSettings" />
            <div class="upload-progress">
                <div class="progress">
                    <div
                        class="upload-progress-bar progress-bar progress-bar-success"
                        :style="{ width: `${percentageInt}%` }" />
                    <div class="upload-percentage">{{ percentageInt }}%</div>
                </div>
            </div>
            <div>
                <FontAwesomeIcon v-if="['running', 'queued'].includes(status)" icon="fa-spinner" spin />
                <FontAwesomeIcon
                    v-else-if="status === 'error'"
                    class="cursor-pointer"
                    icon="fa-exclamation-triangle"
                    @click="removeUpload" />
                <FontAwesomeIcon
                    v-else-if="status === 'init'"
                    class="cursor-pointer"
                    icon="fa-trash"
                    @click="removeUpload" />
                <FontAwesomeIcon
                    v-else-if="status === 'success'"
                    class="cursor-pointer"
                    icon="fa-check"
                    @click="removeUpload" />
                <FontAwesomeIcon v-else icon="fa-exclamation" />
            </div>
        </div>
        <div v-if="info" v-localize class="upload-info-text">
            {{ info }}
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
