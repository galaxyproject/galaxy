<script setup lang="ts">
import { faCopy, faEdit, faFolderOpen, faLaptop } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import Vue, { computed, type Ref, ref } from "vue";
import { useRouter } from "vue-router/composables";

import type { HDASummary } from "@/api";
import type { CollectionBuilderType } from "@/components/History/adapters/buildCollectionModal";
import { monitorUploadedHistoryItems } from "@/composables/monitorUploadedHistoryItems";
import type { DbKey, ExtensionDetails } from "@/composables/uploadConfigurations";
import { archiveExplorerEventBus, type ArchiveSource } from "@/composables/zipExplorer";
import { filesDialog } from "@/utils/dataModals";
import { UploadQueue } from "@/utils/upload-queue.js";

import type { ComponentSize } from "../BaseComponents/componentVariants";
import { defaultModel, isLocalFile, type UploadFile, type UploadItem } from "./model";
import { COLLECTION_TYPES, DEFAULT_FILE_NAME, hasBrowserSupport } from "./utils";

import GButton from "../BaseComponents/GButton.vue";
import DefaultRow from "./DefaultRow.vue";
import UploadBox from "./UploadBox.vue";
import UploadSelect from "./UploadSelect.vue";
import UploadSelectExtension from "./UploadSelectExtension.vue";
import CollectionCreatorIndex from "@/components/Collections/CollectionCreatorIndex.vue";

const router = useRouter();

interface Props {
    chunkUploadSize: number;
    defaultDbKey: string;
    defaultExtension: string;
    effectiveExtensions: ExtensionDetails[];
    fileSourcesConfigured: boolean;
    ftpUploadSite?: string;
    historyId: string;
    multiple?: boolean;
    hasCallback?: boolean;
    lazyLoad?: number;
    listDbKeys: DbKey[];
    isCollection?: boolean;
    disableFooter?: boolean;
    emitUploaded?: boolean;
    size?: ComponentSize;
}

const props = withDefaults(defineProps<Props>(), {
    ftpUploadSite: undefined,
    multiple: true,
    lazyLoad: 150,
    size: "medium",
    isCollection: false,
});

const emit = defineEmits<{
    (e: "dismiss"): void;
    (e: "progress", value: number | null, variant?: string): void;
    (e: "uploaded", value: HDASummary[]): void;
}>();

const collectionModalShow = ref(false);
const collectionType = ref<CollectionBuilderType>("list");
const counterAnnounce = ref(0);
const counterError = ref(0);
const counterRunning = ref(0);
const counterSuccess = ref(0);
const extension = ref(props.defaultExtension);
const dbKey = ref(props.defaultDbKey);
const queueStopping = ref(false);
const uploadCompleted = ref(0);
const uploadFile = ref<HTMLInputElement | null>(null);
const uploadItems = ref<Record<string, UploadItem>>({});
const uploadSize = ref(0);
const queue = ref(createUploadQueue());
const selectedItemsForModal = ref<HDASummary[]>([]);

const counterNonRunning = computed(() => counterAnnounce.value + counterSuccess.value + counterError.value);
const creatingPairedType = computed(
    () => props.isCollection && ["list:paired", "paired"].includes(collectionType.value)
);
const enableBuild = computed(
    () =>
        !isRunning.value &&
        counterAnnounce.value == 0 &&
        counterSuccess.value > 0 &&
        uploadedHistoryItemsReady.value &&
        uploadedHistoryItemsOk.value.length > 0 &&
        (!creatingPairedType.value || uploadedHistoryItemsOk.value.length % 2 === 0)
);
const enableReset = computed(() => !isRunning.value && counterNonRunning.value > 0);
const enableStart = computed(() => !isRunning.value && counterAnnounce.value > 0);
const enableSources = computed(() => !isRunning.value && (props.multiple || counterNonRunning.value == 0));
const isRunning = computed(() => counterRunning.value > 0);
const hasRemoteFiles = computed(() => props.fileSourcesConfigured || !!props.ftpUploadSite);
const historyId = computed(() => props.historyId);
const listExtensions = computed(() => props.effectiveExtensions.filter((ext) => !ext.composite_files));
const showHelper = computed(() => Object.keys(uploadItems.value).length === 0);
const uploadValues = computed(() => Object.values(uploadItems.value));

const { uploadedHistoryItemsOk, uploadedHistoryItemsReady, historyItemsStateInfo } = monitorUploadedHistoryItems(
    uploadValues as Ref<UploadItem[]>,
    historyId,
    enableStart,
    creatingPairedType
);

function createUploadQueue() {
    return new UploadQueue({
        announce: eventAnnounce,
        chunkSize: props.chunkUploadSize,
        complete: eventComplete,
        error: eventError,
        get: (index: string) => uploadItems.value[index],
        multiple: props.multiple,
        progress: eventProgress,
        success: eventSuccess,
        warning: eventWarning,
    });
}

/** Add files to queue */
function addFiles(files: FileList, immediate = false) {
    if (!isRunning.value) {
        if (immediate || !props.multiple) {
            eventReset();
        }
        if (props.multiple) {
            queue.value.add(files);
        } else if (files.length > 0) {
            queue.value.add([files[0]]);
        }
    }
}

function addFileFromInput(eventTarget: EventTarget | null) {
    if (!eventTarget) {
        return;
    }
    const { files } = eventTarget as HTMLInputElement;
    if (files) {
        addFiles(files);
    }
}

/** A new file has been announced to the upload queue */
function eventAnnounce(index: string, file: UploadFile) {
    counterAnnounce.value++;
    const mode = file.mode || "local";
    let deferred: boolean | undefined = false;
    if (mode === "local") {
        deferred = undefined;
    }
    const uploadModel = {
        ...defaultModel,
        id: index,
        dbKey: dbKey.value,
        extension: extension.value,
        fileData: file,
        fileMode: mode,
        deferred: deferred,
        fileName: file.name,
        filePath: file.path,
        fileSize: file.size,
        fileUri: file.uri,
    };
    Vue.set(uploadItems.value, index, uploadModel);
}

/** Populates and opens collection builder with uploaded files, or emits uploads */
async function eventBuild(openModal = false) {
    if (openModal) {
        selectedItemsForModal.value = uploadedHistoryItemsOk.value;
        collectionModalShow.value = true;
    } else {
        emit("uploaded", uploadedHistoryItemsOk.value);
    }
    counterRunning.value = 0;
    eventReset();
    emit("dismiss");
}

/** Queue is done */
function eventComplete() {
    uploadValues.value.forEach((model) => {
        if (model.status === "queued") {
            model.status = "init";
        }
    });
    counterRunning.value = 0;
    queueStopping.value = false;
}

/** Create a new file */
function eventCreate() {
    queue.value.add([{ name: DEFAULT_FILE_NAME, size: 0, mode: "new" }]);
}

/** Error */
function eventError(index: string, message: string) {
    const it = uploadItems.value[index];
    if (it) {
        it.percentage = 100;
        it.status = "error";
        it.info = message;
        uploadCompleted.value += it.fileSize * 100;
        counterAnnounce.value--;
        counterError.value++;
        emit("progress", uploadPercentage(100, it.fileSize), "danger");
    }
}

/** Update model */
function eventInput(index: string, newData: Partial<UploadItem>) {
    const it = uploadItems.value[index];
    if (it) {
        Object.entries(newData).forEach(([key, value]) => {
            (it as any)[key] = value;
        });
    }
}

/** Reflect upload progress */
function eventProgress(index: string, percentage: number) {
    const it = uploadItems.value[index];
    if (it) {
        it.percentage = percentage;
        emit("progress", uploadPercentage(percentage, it.fileSize));
    }
}

/** Remove model from upload list */
function eventRemove(index: string) {
    const it = uploadItems.value[index];
    if (it) {
        var status = it.status;
        if (status == "success") {
            counterSuccess.value--;
        } else if (status == "error") {
            counterError.value--;
        } else {
            counterAnnounce.value--;
        }
        Vue.delete(uploadItems.value, index);
        queue.value.remove(index);
    }
}

async function eventExplore(archiveSource: ArchiveSource) {
    await router.push({ name: "ZipImportWizard" });
    archiveExplorerEventBus.emit("set-archive-source", archiveSource);
    emit("dismiss");
}

/** Show remote files dialog or FTP files */
function eventRemoteFiles() {
    filesDialog(
        (items: UploadFile[]) => {
            queue.value.add(
                items.map((item) => {
                    const rval = {
                        mode: "url",
                        name: item.label,
                        size: item.size,
                        path: item.url,
                    };
                    return rval;
                })
            );
        },
        { multiple: true },
        (route: string) => {
            router.push(route);
            emit("dismiss");
        }
    );
}

/** Remove all */
function eventReset() {
    if (!isRunning.value) {
        counterAnnounce.value = 0;
        counterSuccess.value = 0;
        counterError.value = 0;
        queue.value.reset();
        uploadItems.value = {};
        extension.value = props.defaultExtension;
        dbKey.value = props.defaultDbKey;
        emit("progress", 0);
    }
}

/** Success */
function eventSuccess(index: string, incoming: any) {
    var it = uploadItems.value[index];
    if (it) {
        it.percentage = 100;
        it.status = "success";
        it.outputs = incoming.outputs || incoming.data.outputs || {};
        emit("progress", uploadPercentage(100, it.fileSize));
        uploadCompleted.value += it.fileSize * 100;
        counterAnnounce.value--;
        counterSuccess.value++;
    }
}

/** Start upload process */
function eventStart() {
    if (!isRunning.value && counterAnnounce.value > 0) {
        uploadSize.value = 0;
        uploadCompleted.value = 0;
        uploadValues.value.forEach((model) => {
            if (model.status === "init") {
                model.status = "queued";
                if (!model.targetHistoryId) {
                    // Associate with current history once upload starts
                    // This will not change if the current history is changed during upload
                    model.targetHistoryId = historyId.value;
                }
                uploadSize.value += model.fileSize;
            }
        });
        emit("progress", 0, "success");
        counterRunning.value = counterAnnounce.value;
        queue.value.start();
    }
}

/** Pause upload process */
function eventStop() {
    if (isRunning.value) {
        emit("progress", null, "info");
        queueStopping.value = true;
        queue.value.stop();
    }
}

/** Display warning */
function eventWarning(index: string, message: string) {
    const it = uploadItems.value[index];
    if (it) {
        it.status = "warning";
        it.info = message;
    }
}

/** Update collection type */
function updateCollectionType(newCollectionType: CollectionBuilderType) {
    collectionType.value = newCollectionType;
}

/* Update extension type for all entries */
function updateExtension(newExtension: string) {
    extension.value = newExtension;
    uploadValues.value.forEach((model) => {
        if (model.status === "init" && model.extension === props.defaultExtension) {
            model.extension = newExtension;
        }
    });
}

/** Update reference dataset for all entries */
function updateDbKey(newDbKey: string) {
    dbKey.value = newDbKey;
    uploadValues.value.forEach((model) => {
        if (model.status === "init" && model.dbKey === props.defaultDbKey) {
            model.dbKey = newDbKey;
        }
    });
}

/** Calculate percentage of all queued uploads */
function uploadPercentage(percentage: number, size: number) {
    return (uploadCompleted.value + percentage * size) / uploadSize.value;
}

defineExpose({
    addFiles,
    counterAnnounce,
    listExtensions,
    showHelper,
});
</script>

<template>
    <div class="upload-wrapper">
        <div class="upload-header">
            <div v-if="queueStopping" v-localize>Queue will pause after completing the current file...</div>
            <div v-else-if="counterAnnounce === 0">
                <div v-if="!!hasBrowserSupport">&nbsp;</div>
                <div v-else>
                    Browser does not support Drag & Drop. Try Firefox 4+, Chrome 7+, IE 10+, Opera 12+ or Safari 6+.
                </div>
            </div>
            <div v-else>
                <div v-if="!isRunning">
                    You added {{ counterAnnounce }} file(s) to the queue. Add more files or click 'Start' to proceed.
                </div>
                <div v-else>Please wait...{{ counterAnnounce }} out of {{ counterRunning }} remaining...</div>
            </div>
        </div>
        <UploadBox @add="addFiles">
            <div v-show="showHelper" class="upload-helper">
                <FontAwesomeIcon class="mr-1" :icon="faCopy" />
                <span v-localize>Drop files here</span>
            </div>
            <div v-show="!showHelper">
                <DefaultRow
                    v-for="[uploadIndex, uploadItem] in Object.entries(uploadItems).slice(0, lazyLoad)"
                    :key="uploadIndex"
                    :index="uploadIndex"
                    :db-key="uploadItem.dbKey"
                    :deferred="uploadItem.deferred"
                    :extension="uploadItem.extension"
                    :file-data="isLocalFile(uploadItem.fileData) ? uploadItem.fileData : undefined"
                    :file-content="uploadItem.fileContent"
                    :file-mode="uploadItem.fileMode"
                    :file-name="uploadItem.fileName"
                    :file-size="uploadItem.fileSize"
                    :info="uploadItem.info || undefined"
                    :list-extensions="!isCollection && listExtensions.length > 1 ? listExtensions : undefined"
                    :list-db-keys="!isCollection && listDbKeys.length > 1 ? listDbKeys : undefined"
                    :percentage="uploadItem.percentage"
                    :space-to-tab="uploadItem.spaceToTab"
                    :status="uploadItem.status"
                    :to-posix-lines="uploadItem.toPosixLines"
                    @remove="eventRemove"
                    @input="eventInput"
                    @explore="eventExplore" />
                <div
                    v-if="uploadValues.length > lazyLoad"
                    v-localize
                    class="upload-text-message"
                    data-description="lazyload message">
                    Only showing first {{ lazyLoad }} of {{ uploadValues.length }} entries.
                </div>
            </div>
            <label class="sr-only" for="upload-file">Uploaded File</label>
            <input
                id="upload-file"
                ref="uploadFile"
                type="file"
                :multiple="multiple"
                @change="addFileFromInput($event.target)" />
        </UploadBox>
        <div v-if="!disableFooter" class="upload-footer text-center">
            <span v-if="isCollection" class="upload-footer-title">Collection:</span>
            <UploadSelect
                v-if="isCollection"
                class="upload-footer-collection-type"
                :value="collectionType"
                :disabled="isRunning"
                :options="COLLECTION_TYPES"
                :searchable="false"
                placeholder="Select Type"
                @input="updateCollectionType" />
            <span class="upload-footer-title">Type (set all):</span>
            <UploadSelectExtension
                class="upload-footer-extension"
                :value="extension"
                :disabled="isRunning"
                :list-extensions="listExtensions"
                @input="updateExtension">
            </UploadSelectExtension>
            <span class="upload-footer-title">Reference (set all):</span>
            <UploadSelect
                class="upload-footer-genome"
                :value="dbKey"
                :disabled="isRunning"
                :options="listDbKeys"
                what="reference"
                placeholder="Select Reference"
                @input="updateDbKey" />
        </div>
        <slot name="footer" />
        <div
            class="d-flex justify-content-end flex-wrap"
            :class="{
                'upload-buttons': !disableFooter,
                'flex-gapx-1': disableFooter,
            }">
            <GButton id="btn-local" :size="size" :disabled="!enableSources" @click="uploadFile?.click()">
                <FontAwesomeIcon :icon="faLaptop" />
                <span v-localize>Choose local file</span>
            </GButton>
            <GButton
                v-if="hasRemoteFiles"
                id="btn-remote-files"
                :size="size"
                :disabled="!enableSources"
                @click="eventRemoteFiles">
                <FontAwesomeIcon :icon="faFolderOpen" />
                <span v-localize>Choose from repository</span>
            </GButton>
            <GButton id="btn-new" :size="size" title="Paste/Fetch data" :disabled="!enableSources" @click="eventCreate">
                <FontAwesomeIcon :icon="faEdit" />
                <span v-localize>Paste/Fetch data</span>
            </GButton>
            <GButton
                id="btn-start"
                :size="size"
                :disabled="!enableStart"
                title="Start"
                :variant="enableStart ? 'primary' : null"
                @click="eventStart">
                <span v-localize>Start</span>
            </GButton>
            <GButton
                v-if="isCollection"
                id="btn-build"
                :size="size"
                :disabled="!enableBuild"
                :tooltip="!enableBuild && Boolean(historyItemsStateInfo?.message)"
                :disabled-title="historyItemsStateInfo?.message || 'Build is not available'"
                title="Build"
                :color="historyItemsStateInfo?.color ? historyItemsStateInfo.color : undefined"
                @click="() => eventBuild(true)">
                <FontAwesomeIcon
                    v-if="historyItemsStateInfo?.icon"
                    :icon="historyItemsStateInfo.icon"
                    :spin="historyItemsStateInfo.spin" />
                <span v-localize>Build</span>
            </GButton>
            <GButton
                v-if="emitUploaded"
                id="btn-emit"
                :size="size"
                :disabled="!enableBuild"
                :tooltip="Boolean(historyItemsStateInfo?.message)"
                :disabled-title="historyItemsStateInfo?.message || 'Upload Valid Files to Use'"
                :title="historyItemsStateInfo?.message || 'Use Uploaded Files'"
                :color="historyItemsStateInfo?.color ? historyItemsStateInfo.color : undefined"
                @click="() => eventBuild(false)">
                <FontAwesomeIcon
                    v-if="historyItemsStateInfo?.icon"
                    :icon="historyItemsStateInfo.icon"
                    :spin="historyItemsStateInfo.spin" />
                <span v-localize>Use Uploaded</span>
                <span v-if="uploadedHistoryItemsOk.length < counterSuccess">
                    ({{ uploadedHistoryItemsOk.length }}/{{ counterSuccess }})
                </span>
                <span v-else> ({{ counterSuccess }}) </span>
            </GButton>
            <GButton id="btn-stop" :size="size" title="Pause" :disabled="!isRunning" @click="eventStop">
                <span v-localize>Pause</span>
            </GButton>
            <GButton id="btn-reset" :size="size" title="Reset" :disabled="!enableReset" @click="eventReset">
                <span v-localize>Reset</span>
            </GButton>
            <GButton id="btn-close" :size="size" title="Close" @click="$emit('dismiss')">
                <span v-if="hasCallback" v-localize>Cancel</span>
                <span v-else v-localize>Close</span>
            </GButton>
        </div>
        <CollectionCreatorIndex
            v-if="isCollection && historyId"
            :history-id="historyId"
            :collection-type="collectionType"
            :selected-items="selectedItemsForModal"
            :show.sync="collectionModalShow"
            default-hide-source-items />
    </div>
</template>
