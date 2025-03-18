<script setup lang="ts">
import { faArchive, faLaptop } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import axios from "axios";
import { BButton } from "bootstrap-vue";
import { ROCrateZipExplorer, type ZipArchive } from "ro-crate-zip-explorer";
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router/composables";

import { withPrefix } from "@/utils/redirect";
import { errorMessageAsString } from "@/utils/simple-error";

import { isZipFile } from "./utils";

import ZipDropZone from "./ZipDropZone.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    hasCallback: boolean;
}

defineProps<Props>();

const router = useRouter();

const fileInputRef = ref<HTMLInputElement>();
const localZipFile = ref<File>();
const zipUrl = ref<string>();
const errorMessage = ref<string>();
const loadingPreview = ref(false);

const zipArchive = ref<ZipArchive>();
const zipExplorer = ref<ROCrateZipExplorer>();

const showHelper = computed(() => !loadingPreview.value && !zipArchive.value);
const canStart = computed(() => Boolean(zipArchive.value));
const canOpenUrl = computed(() => ensureValidUrl(zipUrl.value) !== undefined);

function browseZipFile() {
    fileInputRef.value?.click();
}

async function onFileChange(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0] ?? null;

    errorMessage.value = isZipFile(file);
    if (!errorMessage.value) {
        await exploreLocalZip(file!);
    }
}

// async function start() {
//     if (!zipArchive.value) {
//         return;
//     }

//     const selectedPaths = selectedFiles.value.map((item) => item.path);
//     const selectedZipEntries = zipArchive.value.entries.filter((entry) => selectedPaths.includes(entry.path));
//     // Combine selected items with their corresponding zip entries into a new array

//     if (zipUrl.value !== undefined) {
//         const toUploadToHistory = [];
//         for (const item of selectedFiles.value) {
//             const entry = zipArchive.value.entries.find((e) => e.path === item.path);
//             if (!entry) {
//                 continue;
//             }
//             const extractUrl = toExtractUrl(entry as ZipFileEntry);
//             console.log("Selected REMOTE entry:", extractUrl, item);
//             if (isWorkflowFile(item)) {
//                 const response = await axios.post(withPrefix("/api/workflows"), { archive_source: extractUrl });
//                 console.log("Response:", response);
//             } else {
//                 toUploadToHistory.push(entry);
//             }
//         }
//         if (toUploadToHistory.length > 0) {
//             const elements = toUploadToHistory.map((entry) => {
//                 const extractUrl = toExtractUrl(entry as ZipFileEntry);
//                 return {
//                     name: entry.path.split("/").pop() ?? "unknown",
//                     deferred: false,
//                     src: "url",
//                     url: extractUrl,
//                     // dbkey: item.dbKey ?? "?",
//                     // ext: item.extension ?? "auto",
//                     // space_to_tab: item.spaceToTab,
//                     // to_posix_lines: item.toPosixLines,
//                 };
//             });
//             const target = {
//                 destination: { type: "hdas" },
//                 elements: elements,
//             };
//             const payload = {
//                 history_id: props.historyId,
//                 targets: [target],
//             };
//             const response = await axios.post(withPrefix("/api/tools/fetch"), payload);
//             console.log("Response:", response);
//         }
//     }
//     //TODO: handle local zip files. This will require downloading the compressed file to a temporary location and then extracting and uploading the selected files.

//     console.log("Selected entries:", selectedZipEntries);
// }

// function toExtractUrl(entry: ZipFileEntry): string {
//     return `zip://extract?source=${zipUrl.value}&header_offset=${entry.headerOffset}&compress_size=${entry.compressSize}&compression_method=${entry.compressionMethod}`;
// }

function start() {
    router.push({ name: "ZipImportWizard" });
}

function reset() {
    localZipFile.value = undefined;
    zipUrl.value = undefined;
    errorMessage.value = undefined;
    zipArchive.value = undefined;
    zipExplorer.value = undefined;
}

function onDropError(message: string) {
    errorMessage.value = message;
}

async function exploreLocalZip(file: File) {
    localZipFile.value = file;
    return openZip(file);
}

async function exploreRemoteZip() {
    if (!zipUrl.value) {
        return;
    }

    // // TODO: this is obviously not the right way to get the full URL
    // // but getApiRoot() only returns "/" here.
    const appRoot = window.location.origin;

    const proxyUrl = `${appRoot}/api/proxy?url=${encodeURIComponent(zipUrl.value)}`;
    // const proxyUrl = withPrefix(`/api/proxy?url=${encodeURIComponent(zipUrl.value)}`);

    return openZip(proxyUrl);
}

async function openZip(zipSource: File | string) {
    errorMessage.value = undefined;
    loadingPreview.value = true;
    try {
        const explorer = new ROCrateZipExplorer(zipSource);
        zipArchive.value = await explorer.open();
    } catch (e) {
        errorMessage.value = errorMessageAsString(e);
    } finally {
        loadingPreview.value = false;
    }
}

function ensureValidUrl(url?: string): string | undefined {
    if (!url) {
        return undefined;
    }
    try {
        new URL(url);
        return url;
    } catch (e) {
        errorMessage.value = "Invalid URL provided";
        return undefined;
    }
}

watch(canOpenUrl, (newValue, oldValue) => {
    // Clear error message when URL becomes valid
    if (oldValue === false && newValue === true) {
        errorMessage.value = undefined;
    }
});
</script>

<template>
    <div class="upload-wrapper">
        <div class="upload-header">
            <div v-if="errorMessage" v-localize class="text-danger">{{ errorMessage }}</div>
            <div v-else v-localize>
                Browse the contents of a Zip archive and select individual files to import without uploading the whole
                archive
            </div>
        </div>

        <div class="upload-box">
            <ZipDropZone v-if="showHelper" @dropError="onDropError" @dropSuccess="exploreLocalZip" />
            <div v-else>
                <LoadingSpan v-if="loadingPreview" message="Checking ZIP contents..." />
                <!-- <RoCrateExplorer
                    v-else-if="rocrateSummary"
                    :crate-summary="rocrateSummary"
                    :selected-items="selectedFiles"
                    @update:selected-items="onSelectedItemsUpdate" /> -->
            </div>
        </div>

        <div class="upload-footer">
            <label v-localize class="upload-footer-title" for="rocrate-zip-url">RO-Crate Zip URL:</label>
            <input id="rocrate-zip-url" v-model="zipUrl" type="text" size="50" />

            <BButton id="btn-open" title="Open ZIP URL" size="sm" :disabled="!canOpenUrl" @click="exploreRemoteZip">
                <FontAwesomeIcon :icon="faArchive" />
                <span v-localize>Open Zip URL</span>
            </BButton>
        </div>

        <div class="upload-buttons d-flex justify-content-end">
            <BButton id="btn-local" @click="browseZipFile">
                <FontAwesomeIcon :icon="faLaptop" />
                <span v-localize>Choose local file</span>
            </BButton>

            <label style="display: none">
                <input ref="fileInputRef" type="file" accept=".zip" @change="onFileChange" />
            </label>

            <BButton
                id="btn-start"
                :disabled="!canStart"
                title="Start"
                :variant="canStart ? 'primary' : null"
                @click="start">
                <span v-localize>Start exploring</span>
            </BButton>

            <BButton id="btn-reset" title="Reset" @click="reset">
                <span v-localize>Reset</span>
            </BButton>

            <BButton id="btn-close" title="Close" @click="$emit('dismiss')">
                <span v-if="hasCallback" v-localize>Close</span>
                <span v-else v-localize>Cancel</span>
            </BButton>
        </div>
    </div>
</template>
