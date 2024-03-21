<script setup>
import { library } from "@fortawesome/fontawesome-svg-core";
import { faEdit, faFolderOpen, faLaptop } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { bytesToString } from "utils/utils";
import { computed, onMounted, ref } from "vue";

import UploadExtension from "./UploadExtension.vue";
import UploadSelect from "./UploadSelect.vue";
import UploadSettings from "./UploadSettings.vue";

library.add(faEdit, faLaptop, faFolderOpen);

const fileField = ref(null);

const props = defineProps({
    deferred: {
        type: Boolean,
        default: null,
    },
    extension: {
        type: String,
        required: true,
    },
    fileContent: {
        type: String,
        required: true,
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
    dbKey: {
        type: String,
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
    listDbKeys: {
        type: Array,
        default: null,
    },
    listExtensions: {
        type: Array,
        default: null,
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

const emit = defineEmits(["input", "remove"]);

const isDisabled = computed(() => props.status !== "init");
function inputExtension(newExtension) {
    emit("input", props.index, { extension: newExtension });
}

function inputFileContent(newFileContent) {
    emit("input", props.index, { fileContent: newFileContent, fileSize: newFileContent.length });
}

function inputFileName(newFileName) {
    emit("input", props.index, { fileName: newFileName });
}

function inputDbKey(newDbKey) {
    emit("input", props.index, { dbKey: newDbKey });
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

onMounted(() => {
    autoSelectFileInput();
});

function autoSelectFileInput() {
    fileField.value.select();
}
</script>

<template>
    <div :id="`upload-row-${index}`" class="upload-row rounded my-1 p-2" :class="`upload-${status}`">
        <div class="d-flex justify-content-around">
            <div>
                <FontAwesomeIcon v-if="fileMode == 'new'" icon="fa-edit" fixed-width />
                <FontAwesomeIcon v-if="fileMode == 'local'" icon="fa-laptop" fixed-width />
                <FontAwesomeIcon v-if="fileMode == 'url'" icon="fa-folder-open" fixed-width />
            </div>
            <b-input
                ref="fileField"
                :value="fileName"
                class="upload-title p-1 border rounded"
                :disabled="isDisabled"
                @input="inputFileName" />
            <div class="upload-size">
                {{ bytesToString(fileSize) }}
            </div>
            <UploadSelect
                v-if="listExtensions !== null"
                class="upload-extension"
                :value="extension"
                :disabled="isDisabled"
                :options="listExtensions"
                placeholder="Select Type"
                what="file type"
                @input="inputExtension" />
            <UploadExtension v-if="listExtensions !== null" :extension="extension" :list-extensions="listExtensions" />
            <UploadSelect
                v-if="listDbKeys !== null"
                class="upload-genome"
                :value="dbKey"
                :disabled="isDisabled"
                :options="listDbKeys"
                placeholder="Select Reference"
                what="reference"
                @input="inputDbKey" />
            <UploadSettings
                class="upload-settings"
                :deferred="deferred"
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
                <FontAwesomeIcon v-if="['running', 'queued'].includes(status)" icon="fa-spinner" spin />
                <FontAwesomeIcon
                    v-else-if="status === 'error'"
                    class="cursor-pointer"
                    icon="fa-exclamation-triangle"
                    fixed-width
                    @click="removeUpload" />
                <FontAwesomeIcon
                    v-else-if="status === 'init'"
                    class="cursor-pointer"
                    icon="fa-trash"
                    fixed-width
                    @click="removeUpload" />
                <FontAwesomeIcon
                    v-else-if="status === 'success'"
                    class="cursor-pointer"
                    icon="fa-check"
                    fixed-width
                    @click="removeUpload" />
                <FontAwesomeIcon v-else icon="fa-exclamation" />
            </div>
        </div>
        <div v-if="info" v-localize class="upload-text-message font-weight-bold">
            {{ info }}
        </div>
        <div v-if="fileMode == 'new'">
            <div class="upload-text-message">
                Download data from the web by entering URLs (one per line) or directly paste content.
            </div>
            <b-textarea
                :value="fileContent"
                class="upload-text-content form-control"
                :disabled="isDisabled"
                @input="inputFileContent" />
        </div>
    </div>
</template>
