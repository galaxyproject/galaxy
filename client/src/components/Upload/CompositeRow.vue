<script setup>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCheck, faEdit, faExclamation, faFolderOpen, faLaptop } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BDropdown, BDropdownItem } from "bootstrap-vue";
import { bytesToString } from "utils/utils";
import { computed, ref } from "vue";
import { openFileDialog } from "./utils";

import UploadSettings from "./UploadSettings.vue";
import UploadSettingsSelect from "./UploadSettingsSelect.vue";

library.add(faCheck, faEdit, faExclamation, faFolderOpen, faLaptop);

const props = defineProps({
    extension: String,
    fileContent: String,
    fileDescription: String,
    fileName: String,
    fileSize: Number,
    genome: String,
    index: String,
    info: String,
    percentage: Number,
    space_to_tab: Boolean,
    status: String,
    to_posix_lines: Boolean,
});

const emit = defineEmits();

const fileMode = ref("");

const percentageInt = computed(() => parseInt(props.percentage || 0));

function inputFileContent(newFileContent) {
    emit("input", props.index, { file_content: newFileContent, file_size: newFileContent.length });
}

function inputDialog(index) {
    openFileDialog((files) => {
        if (props.status !== "running" && files && files.length > 0) {
            emit("input", index, {
                chunk_mode: true,
                file_data: files[0],
                file_name: files[0].name,
                file_size: files[0].size,
                file_mode: files[0].mode || "local",
            });
        }
    });
}

function inputPaste() {
    fileMode.value = "new";
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
    <div :id="`upload-row-${index}`" class="upload-row rounded p-2" :class="`upload-${status}`">
        <div class="d-flex justify-content-around">
            <div>
                <BDropdown
                    :id="`upload-type-${index}`"
                    text="Select"
                    size="sm"
                    button-class="upload-type-dropdown py-0 px-1">
                    <BDropdownItem @click="inputDialog(index)">
                        <FontAwesomeIcon icon="fa-laptop" />
                        <span v-localize>Choose local file</span>
                    </BDropdownItem>
                    <BDropdownItem @click="inputPaste">
                        <FontAwesomeIcon icon="fa-edit" />
                        <span v-localize>Paste/Fetch data</span>
                    </BDropdownItem>
                </BDropdown>
            </div>
            <div class="upload-title">
                {{ fileDescription }}
            </div>
            <div class="upload-size">
                {{ bytesToString(fileSize) }}
            </div>
            <UploadSettings :to_posix_lines="to_posix_lines" :space_to_tab="space_to_tab" @input="inputSettings" />
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
                <FontAwesomeIcon v-else-if="status === 'error'" icon="fa-exclamation-triangle" />
                <FontAwesomeIcon v-else-if="fileSize > 0" icon="fa-check" />
                <FontAwesomeIcon v-else icon="fa-exclamation" />
            </div>
        </div>
        <div v-if="info" class="upload-info-text" v-localize>
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
button {
    padding: 20px !important;
    font-size: $h2-font-size !important;
}
.upload-text-content {
    width: 100%;
    height: 80px;
    background: inherit;
    color: $text-color;
    white-space: pre;
    overflow: auto;
}
</style>
