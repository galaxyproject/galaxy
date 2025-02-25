<script setup lang="ts">
import { faArchive, faLaptop } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import { validateSingleZip } from "./rocrate.utils";

import RoCrateExplorer from "./RoCrateExplorer.vue";
import ZipDropZone from "./ZipDropZone.vue";

interface Props {
    historyId: string;
    hasCallback: boolean;
}

defineProps<Props>();

const fileInputRef = ref<HTMLInputElement>();
const localZipFile = ref<File>();
const zipUrl = ref<string>();
const errorMessage = ref<string>();

const showHelper = computed(() => !localZipFile.value);
const canStart = computed(() => true);
const canOpenUrl = computed(() => ensureValidUrl(zipUrl.value) !== undefined);

function browseZipFile() {
    fileInputRef.value?.click();
}

function onFileChange(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0] ?? null;
    errorMessage.value = validateSingleZip(file);
    if (!errorMessage.value) {
        exploreZip(file!);
    }
}

function openUrl() {
    console.log("Open URL");
}

function start() {
    console.log("Start");
}

function reset() {
    console.log("Reset");

    localZipFile.value = undefined;
    zipUrl.value = undefined;
}

function onDropError(message: string) {
    errorMessage.value = message;
}

function exploreZip(file: File) {
    console.log("Dropped file", file);
    localZipFile.value = file;
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
            <div v-else v-localize>Explore the contents of an RO-Crate Zip file and select files to import</div>
        </div>

        <div class="upload-box">
            <ZipDropZone v-show="showHelper" @dropError="onDropError" @dropSuccess="exploreZip" />
            <RoCrateExplorer v-show="!showHelper" />
            <label style="display: none">
                <input ref="fileInputRef" type="file" accept=".zip" @change="onFileChange" />
            </label>
        </div>

        <div class="upload-footer">
            <label v-localize class="upload-footer-title" for="rocrate-zip-url">RO-Crate Zip URL:</label>
            <input id="rocrate-zip-url" v-model="zipUrl" type="text" size="50" />
            <BButton id="btn-open" title="Open Zip URL" size="sm" :disabled="!canOpenUrl" @click="openUrl">
                <FontAwesomeIcon :icon="faArchive" />
                <span v-localize>Open Zip URL</span>
            </BButton>
        </div>

        <div class="upload-buttons d-flex justify-content-end">
            <BButton id="btn-local" @click="browseZipFile">
                <FontAwesomeIcon :icon="faLaptop" />
                <span v-localize>Choose local file</span>
            </BButton>
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
