<script setup lang="ts">
import { isGalaxyZipExport, isRoCrateZip, useZipExplorer } from "@/composables/zipExplorer";
import { errorMessageAsString } from "@/utils/simple-error";

import GalaxyZipView from "./views/GalaxyZipView.vue";
import RegularZipView from "./views/RegularZipView.vue";
import RoCrateZipView from "./views/RoCrateZipView.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const { isLoading: loadingPreview, zipExplorer, errorMessage, openZip, isSameSource } = useZipExplorer();

const props = defineProps<{
    zipSource: File | string;
}>();

async function loadZip() {
    console.log("Loading ZIP archive:", props.zipSource, zipExplorer.value?.zipArchive.source);
    if (!isSameSource(props.zipSource)) {
        try {
            console.log("OPENING ZIP archive:", props.zipSource);
            await openZip(props.zipSource);
        } catch (error) {
            errorMessage.value = errorMessageAsString(error);
        }
    }
}

loadZip();
</script>

<template>
    <div class="w-100">
        <div v-if="errorMessage" v-localize class="text-danger">{{ errorMessage }}</div>

        <div v-if="zipExplorer">
            <LoadingSpan v-if="loadingPreview" message="Checking ZIP contents..." />
            <RoCrateZipView v-else-if="isRoCrateZip(zipExplorer)" :explorer="zipExplorer" />
            <GalaxyZipView v-else-if="isGalaxyZipExport(zipExplorer)" :explorer="zipExplorer" />
            <RegularZipView v-else-if="zipExplorer" :explorer="zipExplorer" />
        </div>
    </div>
</template>
