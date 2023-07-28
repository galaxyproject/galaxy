<script setup>
import { computed, ref } from "vue";
import Popper from "@/components/Popper/Popper.vue";
import Select2 from "@/components/Select2";
import UploadExtensionDetails from "./UploadExtensionDetails";
import UploadSettings from "./UploadSettings";
import { bytesToString } from "utils/utils";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { library } from "@fortawesome/fontawesome-svg-core";
import { faEdit, faLaptop, faFolderOpen } from "@fortawesome/free-solid-svg-icons";

library.add(faEdit, faLaptop, faFolderOpen);

const props = defineProps({
    listGenomes: Array,
    listExtensions: Array,
    extensions: Array,
    extension: String,
    genome: String,
    index: Number,
    percentage: Number,
    fileContent: String,
    fileMode: String,
    fileName: String,
    fileSize: Number,
    status: String,
    deferred: Boolean,
    to_posix_lines: Boolean,
    space_to_tab: Boolean,
});

const emit = defineEmits();

const percentageInt = computed(() => parseInt(props.percentage || 0));
const extensionDetails = computed(() => props.extensions.find((ext) => ext.id === props.extension) || {});
const extensionDescription = computed(() => extensionDetails.value.description);
const extensionDescriptionUrl = computed(() => extensionDetails.value.description_url);
const removeIcon = computed(() => status_classes[props.status] || status_classes.init);

/** Dictionary of upload states and associated icons */
const status_classes = {
    init: "cursor-pointer fa fa-trash-o",
    queued: "fa fa-spinner fa-spin",
    running: "fa fa-spinner fa-spin",
    success: "cursor-pointer fa fa-check",
    error: "cursor-pointer fa fa-exclamation-triangle",
};

function inputFileContent(newFileContent) {
    emit("input", props.index, { file_content: newFileContent, file_size: newFileContent.length });
}

function inputFileName(newFileName) {
    emit("input", props.index, { file_name: newFileName });
}

function inputSettings(settingId, settingValue) {
    const newSettings = {};
    newSettings[settingId] = settingValue;
    emit("input", props.index, newSettings);
}

function removeUpload() {
    if (["init", "success", "error"].indexOf(props.status) !== -1) {
        emit("remove", props.index);
    }
}
</script>

<template>
    <div :id="`upload-row-${index}`" class="upload-row p-2" :class="{ 'bg-light': index % 2 === 0 }">
        <div class="d-flex justify-content-around">
            <div>
                <FontAwesomeIcon v-if="fileMode == 'new'" icon="fa-edit" />
                <FontAwesomeIcon v-if="fileMode == 'local'" icon="fa-laptop" />
                <FontAwesomeIcon v-if="fileMode == 'ftp'" icon="fa-folder-open" />
            </div>
            <b-input :value="fileName" class="upload-title ml-2 border rounded" @input="inputFileName" />
            <div class="upload-size">
                {{ bytesToString(fileSize) }}
            </div>
            <select2 class="upload-extension" v-model="extension">
                <option v-for="(ext, index) in extensions" :key="index" :value="ext.id">{{ ext.text }}</option>
            </select2>
            <div>
                <UploadExtensionDetails
                    :description="extensionDescription"
                    :description-url="extensionDescriptionUrl" />
            </div>
            <select2 v-model="genome" class="upload-genome">
                <option v-for="(listGenome, index) in listGenomes" :key="index" :value="listGenome.id">
                    {{ listGenome.text }}
                </option>
            </select2>
            <div>
                <UploadSettings
                    :deferred="deferred"
                    :to_posix_lines="to_posix_lines"
                    :space_to_tab="space_to_tab"
                    @input="inputSettings" />
            </div>
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
