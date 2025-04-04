<script setup lang="ts">
import { faArchive, faLaptop } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BButton } from "bootstrap-vue";
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router/composables";

import { isGalaxyZipExport, isRoCrateZip, isZipFile, useZipExplorer } from "@/composables/zipExplorer";

import GalaxyZipView from "./views/GalaxyZipView.vue";
import RegularZipView from "./views/RegularZipView.vue";
import RoCrateZipView from "./views/RoCrateZipView.vue";
import ZipDropZone from "./ZipDropZone.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

interface Props {
    hasCallback: boolean;
}

defineProps<Props>();

const emit = defineEmits(["dismiss"]);

const router = useRouter();

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

const showHelper = computed(() => !loadingPreview.value && !zipExplorer.value);
const canStart = computed(() => Boolean(zipExplorer.value));
const canOpenUrl = computed(() => isValidUrl(zipUrl.value));

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

function dismiss() {
    emit("dismiss");
}

function start() {
    //
    router.push({ name: "ZipImportWizard" });
    dismiss();
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
            <ZipDropZone v-if="showHelper" @dropError="onDropError" @dropSuccess="exploreLocalZip" />
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

            <BButton id="btn-close" title="Close" @click="dismiss">
                <span v-if="hasCallback" v-localize>Close</span>
                <span v-else v-localize>Cancel</span>
            </BButton>
        </div>
    </div>
</template>
