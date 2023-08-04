<script setup>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCheck, faExclamation } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { bytesToString } from "utils/utils";
import { computed, ref } from "vue";

import UploadSettings from "./UploadSettings.vue";
import UploadSettingsSelect from "./UploadSettingsSelect.vue";

library.add(faCheck, faExclamation);

const props = defineProps({
    extension: String,
    fileContent: String,
    fileDescription: String,
    fileMode: String,
    fileName: String,
    fileSize: Number,
    genome: String,
    index: String,
    percentage: Number,
    space_to_tab: Boolean,
    status: String,
    to_posix_lines: Boolean,
});

const emit = defineEmits();

const percentageInt = computed(() => parseInt(props.percentage || 0));

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
                <FontAwesomeIcon v-if="fileSize > 0" icon="fa-check" />
                <FontAwesomeIcon v-else icon="fa-exclamation" class="text-primary" />
            </div>
            <div class="upload-title">
                {{ fileDescription }}
            </div>
            <div class="upload-size">
                {{ bytesToString(fileSize) }}
            </div>
            <UploadSettings :to_posix_lines="to_posix_lines" :space_to_tab="space_to_tab" @input="inputSettings" />
            <div class="upload-info">
                <div class="upload-info-text" />
                <div class="upload-info-progress progress">
                    <div
                        class="upload-progress-bar progress-bar progress-bar-success"
                        :style="{ width: `${percentageInt}%` }" />
                    <div class="upload-percentage">{{ percentageInt }}%</div>
                </div>
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
