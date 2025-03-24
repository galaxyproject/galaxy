<script setup>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faCheck, faEdit, faExclamation, faFolderOpen, faLaptop } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BDropdown, BDropdownItem } from "bootstrap-vue";
import { filesDialog } from "utils/data";
import { bytesToString } from "utils/utils";
import { computed, ref } from "vue";

import { DEFAULT_FILE_NAME } from "./utils";

import UploadSettings from "./UploadSettings.vue";

library.add(faCheck, faEdit, faExclamation, faFolderOpen, faLaptop);

const props = defineProps({
    fileContent: {
        type: String,
        required: true,
    },
    fileDescription: {
        type: String,
        default: null,
    },
    fileMode: {
        type: String,
        required: true,
    },
    fileName: {
        type: String,
        required: true,
    },
    fileSize: {
        type: Number,
        required: true,
    },
    index: {
        type: String,
        required: true,
    },
    info: {
        type: String,
        default: null,
    },
    hasRemoteFiles: {
        type: Boolean,
        default: false,
    },
    optional: {
        type: Boolean,
        required: true,
    },
    percentage: {
        type: Number,
        required: true,
    },
    spaceToTab: {
        type: Boolean,
        required: true,
    },
    status: {
        type: String,
        required: true,
    },
    toPosixLines: {
        type: Boolean,
        required: true,
    },
});

const emit = defineEmits(["input"]);

const isDisabled = computed(() => props.status === "running");
const isDragging = ref(false);
const uploadFile = ref(null);

function inputFileContent(newFileContent) {
    emit("input", props.index, {
        fileContent: newFileContent,
        fileSize: newFileContent.length,
    });
}

function inputDialog(files) {
    if (files && files.length > 0) {
        emit("input", props.index, {
            fileData: files[0],
            fileMode: "local",
            fileName: files[0].name,
            filePath: null,
            fileSize: files[0].size,
        });
    }
}

function inputPaste() {
    emit("input", props.index, {
        fileData: null,
        fileMode: "new",
        fileName: DEFAULT_FILE_NAME,
        filePath: null,
        fileSize: 0,
    });
}

/** Show remote files dialog or FTP files */
function inputRemoteFiles() {
    filesDialog(
        (item) => {
            emit("input", props.index, {
                fileData: null,
                fileMode: "url",
                fileName: item.label,
                filePath: item.url,
                fileSize: item.size,
            });
        },
        { multiple: false }
    );
}

function inputSettings(settingId) {
    const newSettings = {};
    newSettings[settingId] = !props[settingId];
    emit("input", props.index, newSettings);
}

/** Handle files dropped into the upload row **/
function onDrop(evt) {
    isDragging.value = false;
    const droppedFile = evt.dataTransfer && evt.dataTransfer.files && evt.dataTransfer.files[0];
    if (droppedFile) {
        emit("input", props.index, {
            fileData: droppedFile,
            fileMode: "local",
            fileName: droppedFile.name,
            filePath: null,
            fileSize: droppedFile.size,
        });
    }
}
</script>
<template>
    <div
        :id="`upload-row-${index}`"
        class="upload-row rounded my-1 p-2"
        :class="[`upload-${status}`, isDragging && 'bg-warning']"
        @dragover.prevent="isDragging = true"
        @dragleave.prevent="isDragging = false"
        @drop.prevent="onDrop">
        <div class="d-flex justify-content-around">
            <div>
                <BDropdown
                    :id="`upload-type-${index}`"
                    class="upload-source"
                    :disabled="isDisabled"
                    text="选择"
                    :variant="fileSize > 0 ? 'secondary' : 'primary'">
                    <BDropdownItem @click="uploadFile.click()">
                        <FontAwesomeIcon icon="fa-laptop" />
                        <span v-localize>选择本地文件</span>
                    </BDropdownItem>
                    <BDropdownItem v-if="hasRemoteFiles" @click="inputRemoteFiles">
                        <FontAwesomeIcon icon="fa-folder-open" />
                        <span v-localize>选择远程文件</span>
                    </BDropdownItem>
                    <BDropdownItem @click="inputPaste">
                        <FontAwesomeIcon icon="fa-edit" />
                        <span v-localize>粘贴/获取数据</span>
                    </BDropdownItem>
                </BDropdown>
            </div>
            <div class="upload-title">
                {{ fileDescription }}
            </div>
            <div class="upload-title">
                {{ fileName || "-" }}
            </div>
            <div class="upload-size">
                {{ bytesToString(fileSize) }}
            </div>
            <UploadSettings
                :disabled="isDisabled"
                :to-posix-lines="toPosixLines"
                :space-to-tab="spaceToTab"
                @input="inputSettings" />
            <div class="upload-progress">
                <div class="progress">
                    <div
                        class="upload-progress-bar progress-bar progress-bar-success"
                        :style="{ width: `${percentage}%` }" />
                    <div class="upload-percentage">{{ percentage }}%</div>
                </div>
            </div>
            <div>
                <FontAwesomeIcon v-if="['running', 'queued'].includes(status)" icon="fa-spinner" spin fixed-width />
                <FontAwesomeIcon v-else-if="status === 'error'" icon="fa-exclamation-triangle" fixed-width />
                <FontAwesomeIcon v-else-if="fileSize > 0" icon="fa-check" fixed-width />
                <FontAwesomeIcon v-else-if="optional" class="text-info" icon="fa-check" fixed-width />
                <FontAwesomeIcon v-else icon="fa-exclamation" fixed-width />
            </div>
        </div>
        <div v-if="info" v-localize class="upload-text-message font-weight-bold">
            {{ info }}
        </div>
        <div v-if="fileMode == 'new'">
            <div class="upload-text-message">
                通过输入URL地址（每行一个）从网络下载数据或直接粘贴内容。
            </div>
            <b-textarea
                :value="fileContent"
                class="upload-text-content form-control"
                :disabled="isDisabled"
                @input="inputFileContent" />
        </div>
        <input ref="uploadFile" type="file" @change="inputDialog($event.target.files)" />
    </div>
</template>
