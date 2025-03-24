<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faEdit, faFolderOpen, faLaptop } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, onMounted, type Ref, ref } from "vue";

import type { DbKey, ExtensionDetails } from "@/composables/uploadConfigurations";
import { bytesToString } from "@/utils/utils";

import UploadExtension from "./UploadExtension.vue";
import UploadSelect from "./UploadSelect.vue";
import UploadSettings from "./UploadSettings.vue";

library.add(faEdit, faLaptop, faFolderOpen);

const fileField: Ref<HTMLInputElement | null> = ref(null);

interface Props {
    deferred?: boolean;
    extension: string;
    fileContent: string;
    fileMode: string;
    fileName: string;
    fileSize: number;
    dbKey: string;
    index: string;
    info?: string;
    listDbKeys?: DbKey[];
    listExtensions?: ExtensionDetails[];
    percentage: number;
    spaceToTab: boolean;
    status: string;
    toPosixLines: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    deferred: false,
    info: "",
    listDbKeys: undefined,
    listExtensions: undefined,
});

const emit = defineEmits(["input", "remove"]);

const isDisabled = computed(() => props.status !== "init");
function inputExtension(newExtension: string) {
    emit("input", props.index, { extension: newExtension });
}

function inputFileContent(newFileContent: string) {
    emit("input", props.index, { fileContent: newFileContent, fileSize: newFileContent.length });
}

function inputFileName(newFileName: string) {
    emit("input", props.index, { fileName: newFileName });
}

function inputDbKey(newDbKey: string) {
    emit("input", props.index, { dbKey: newDbKey });
}

function inputSettings(settingId: string) {
    const newSettings: Record<string, any> = {};
    newSettings[settingId] = !(props as any)[settingId];
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
    fileField.value?.select();
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
                v-if="listExtensions"
                class="upload-extension"
                :value="extension"
                :disabled="isDisabled"
                :options="listExtensions"
                placeholder="选择类型"
                what="文件类型"
                @input="inputExtension" />
            <UploadExtension v-if="listExtensions" :extension="extension" :list-extensions="listExtensions" />
            <UploadSelect
                v-if="listDbKeys"
                class="upload-genome"
                :value="dbKey"
                :disabled="isDisabled"
                :options="listDbKeys"
                placeholder="选择参考"
                what="参考"
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
                可通过输入网址（每行一个）或直接粘贴内容，从网络下载数据。
            </div>
            <b-textarea
                :value="fileContent"
                class="upload-text-content form-control"
                :disabled="isDisabled"
                @input="inputFileContent" />
        </div>
    </div>
</template>
