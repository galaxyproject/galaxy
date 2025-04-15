<script setup lang="ts">
import { faArchive, faLaptop } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, ref, watch } from "vue";

import { isGalaxyZipExport, isRoCrateZip, isZipFile, useZipExplorer } from "@/composables/zipExplorer";

import GalaxyZipView from "./views/GalaxyZipView.vue";
import RegularZipView from "./views/RegularZipView.vue";
import RoCrateZipView from "./views/RoCrateZipView.vue";
import ZipDropZone from "./ZipDropZone.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const {
    openZip,
    isLoading: loadingPreview,
    zipExplorer,
    errorMessage,
    reset: resetExplorer,
    isValidUrl,
} = useZipExplorer();

const fileInputRef = ref<HTMLInputElement>();
const localZipFile = ref<File>();
const zipUrl = ref<string>();

const canOpenUrl = computed(() => isValidUrl(zipUrl.value));
const showDropZone = computed(() => !loadingPreview.value && !zipExplorer.value);

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

function reset() {
    localZipFile.value = undefined;
    zipUrl.value = undefined;
    resetExplorer();
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
    return openZip(zipUrl.value);
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
            <ZipDropZone v-if="showDropZone" @dropError="onDropError" @dropSuccess="exploreLocalZip" />
            <div v-else>
                <LoadingSpan v-if="loadingPreview" message="Checking ZIP contents..." />
                <RoCrateZipView v-else-if="isRoCrateZip(zipExplorer)" :explorer="zipExplorer" />
                <GalaxyZipView v-else-if="isGalaxyZipExport(zipExplorer)" :explorer="zipExplorer" />
                <RegularZipView v-else-if="zipExplorer" :explorer="zipExplorer" />
            </div>
        </div>

        <div class="upload-footer">
            <label v-localize class="upload-footer-title" for="rocrate-zip-url">RO-Crate Zip URL:</label>
            <input id="rocrate-zip-url" v-model="zipUrl" type="text" size="50" />

            <GButton id="btn-open" title="Open ZIP URL" size="small" :disabled="!canOpenUrl" @click="exploreRemoteZip">
                <FontAwesomeIcon :icon="faArchive" />
                <span v-localize>Open Zip URL</span>
            </GButton>
        </div>

        <div class="upload-buttons d-flex justify-content-end">
            <GButton id="btn-local" @click="browseZipFile">
                <FontAwesomeIcon :icon="faLaptop" />
                <span v-localize>Choose local file</span>
            </GButton>

            <label style="display: none">
                <input ref="fileInputRef" type="file" accept=".zip" @change="onFileChange" />
            </label>

            <GButton id="btn-reset" title="Reset" @click="reset">
                <span v-localize>Reset</span>
            </GButton>
        </div>
    </div>
</template>
