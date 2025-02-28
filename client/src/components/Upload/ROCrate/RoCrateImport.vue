<script setup lang="ts">
import { faArchive, faLaptop } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { type ROCrateZip, ROCrateZipExplorer } from "ro-crate-zip-explorer";
import { computed, ref, watch } from "vue";

import { errorMessageAsString } from "@/utils/simple-error";

import { extractROCrateSummary, type ROCrateFile, type ROCrateSummary, validateLocalZipFile } from "./rocrate.utils";

import RoCrateExplorer from "./RoCrateExplorer.vue";
import ZipDropZone from "./ZipDropZone.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    historyId: string;
    hasCallback: boolean;
}

defineProps<Props>();

const fileInputRef = ref<HTMLInputElement>();
const localZipFile = ref<File>();
const zipUrl = ref<string>();
const errorMessage = ref<string>();
const loadingPreview = ref(false);

const rocrateZip = ref<ROCrateZip>();
const rocrateSummary = ref<ROCrateSummary>();
const selectedItems = ref<ROCrateFile[]>([]);

const showHelper = computed(() => !loadingPreview.value && !rocrateZip.value);
const canStart = computed(() => selectedItems.value.length > 0);
const canOpenUrl = computed(() => ensureValidUrl(zipUrl.value) !== undefined);

function browseZipFile() {
    fileInputRef.value?.click();
}

async function onFileChange(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0] ?? null;

    errorMessage.value = validateLocalZipFile(file);
    if (!errorMessage.value) {
        await exploreLocalZip(file!);
    }
}

function start() {
    console.log("Start", selectedItems.value);
}

function reset() {
    selectedItems.value = [];
    localZipFile.value = undefined;
    zipUrl.value = undefined;
    errorMessage.value = undefined;
    rocrateZip.value = undefined;
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

    // TODO: this is obviously not the right way to get the full URL
    // but getApiRoot() only returns "/" here.
    const appRoot = window.location.origin;

    const proxyUrl = `${appRoot}/api/proxy?url=${encodeURIComponent(zipUrl.value)}`;

    return openZip(proxyUrl);
}

async function openZip(zipSource: File | string) {
    errorMessage.value = undefined;
    loadingPreview.value = true;
    const explorer = new ROCrateZipExplorer(zipSource);
    try {
        rocrateZip.value = await explorer.open();
        rocrateSummary.value = await extractROCrateSummary(rocrateZip.value.crate);
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

function onSelectedItemsUpdate(value: ROCrateFile[]) {
    selectedItems.value = value;
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
            <div v-else v-localize>Explore the contents of an RO-Crate Zip file and select files to import</div>
        </div>

        <div class="upload-box">
            <ZipDropZone v-if="showHelper" @dropError="onDropError" @dropSuccess="exploreLocalZip" />
            <div v-else>
                <LoadingSpan v-if="loadingPreview" message="Loading RO-Crate..." />
                <RoCrateExplorer
                    v-else-if="rocrateSummary"
                    :crate-summary="rocrateSummary"
                    :selected-items="selectedItems"
                    @update:selected-items="onSelectedItemsUpdate" />
            </div>
        </div>

        <div class="upload-footer">
            <label v-localize class="upload-footer-title" for="rocrate-zip-url">RO-Crate Zip URL:</label>
            <input id="rocrate-zip-url" v-model="zipUrl" type="text" size="50" />

            <BButton id="btn-open" title="Open Zip URL" size="sm" :disabled="!canOpenUrl" @click="exploreRemoteZip">
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
                <span v-localize>Start</span>
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
