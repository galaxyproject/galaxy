<script setup lang="ts">
import { faEdit, faFolderOpen, faLaptop } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { useDebounceFn } from "@vueuse/core";
import { storeToRefs } from "pinia";
import { computed, onMounted, type Ref, ref } from "vue";

import type { DbKey, ExtensionDetails } from "@/composables/uploadConfigurations";
import { type ArchiveSource, isLocalZipFile, isRemoteZipFile } from "@/composables/zipExplorer";
import { useUserStore } from "@/stores/userStore";
import { bytesToString } from "@/utils/utils";

import { isLocalFile, type UploadItem } from "./model";

import GButton from "../BaseComponents/GButton.vue";
import UploadExtension from "./UploadExtension.vue";
import UploadSelect from "./UploadSelect.vue";
import UploadSettings from "./UploadSettings.vue";

const { isAnonymous } = storeToRefs(useUserStore());

const fileField: Ref<HTMLInputElement | null> = ref(null);

interface Props {
    deferred?: boolean;
    extension: string;
    fileContent: string;
    fileMode: string;
    fileName: string;
    fileSize: number;
    fileData?: File;
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
    deferred: undefined,
    info: "",
    listDbKeys: undefined,
    listExtensions: undefined,
    fileData: undefined,
});

const emit = defineEmits<{
    (e: "input", index: string, value: Partial<UploadItem>): void;
    (e: "remove", index: string): void;
    (e: "explore", archiveSource: ArchiveSource): void;
}>();

const isExplorable = ref(false);

const isDisabled = computed(() => props.status !== "init");
function inputExtension(newExtension: string) {
    emit("input", props.index, { extension: newExtension });
}

async function inputFileContent(newFileContent: string) {
    emit("input", props.index, { fileContent: newFileContent, fileSize: newFileContent.length });
    isExplorable.value = await isRemoteExplorableArchiveDebounced(newFileContent);
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

const isRemoteExplorableArchiveDebounced = useDebounceFn(async (url: string) => {
    return isRemoteZipFile(url);
}, 1000);

function initializeExplorableArchive() {
    if (props.fileMode === "local" && isLocalFile(props.fileData)) {
        isExplorable.value = isLocalZipFile(props.fileData);
    } else if (props.fileMode === "new" && props.fileContent) {
        isRemoteZipFile(props.fileContent).then((result) => {
            isExplorable.value = result;
        });
    } else {
        // Remote File Source URIs are not explorable because they don't support byte range requests
        isExplorable.value = false;
    }
}

function exploreZipContents() {
    if (props.fileMode === "local" && props.fileData) {
        emit("explore", props.fileData);
    } else if (props.fileMode === "new" && props.fileContent) {
        emit("explore", props.fileContent);
    }
}

initializeExplorableArchive();
</script>

<template>
    <div :id="`upload-row-${index}`" class="upload-row rounded my-1 p-2" :class="`upload-${status}`">
        <div class="d-flex justify-content-around align-items-center">
            <div>
                <FontAwesomeIcon v-if="fileMode == 'new'" :icon="faEdit" fixed-width />
                <FontAwesomeIcon v-if="fileMode == 'local'" :icon="faLaptop" fixed-width />
                <FontAwesomeIcon v-if="fileMode == 'url'" :icon="faFolderOpen" fixed-width />
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
                placeholder="Select Type"
                what="file type"
                @input="inputExtension" />
            <UploadExtension v-if="listExtensions" :extension="extension" :list-extensions="listExtensions" />
            <UploadSelect
                v-if="listDbKeys"
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

            <GButton
                v-if="isExplorable"
                class="btn-explore-archive"
                size="small"
                title="Explore the contents of a remote or local compressed archive and upload individual files"
                :disabled="isAnonymous"
                disabled-title="You must be logged in to use this feature"
                @click="exploreZipContents">
                <span v-localize>Explore</span>
            </GButton>
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
