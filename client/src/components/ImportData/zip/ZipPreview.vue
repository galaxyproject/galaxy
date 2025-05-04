<script setup lang="ts">
import { faCircleNotch } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";

import { type ArchiveSource, isGalaxyZipExport, isRoCrateZip, useZipExplorer } from "@/composables/zipExplorer";

import GalaxyZipView from "./views/GalaxyZipView.vue";
import RegularZipView from "./views/RegularZipView.vue";
import RoCrateZipView from "./views/RoCrateZipView.vue";
import GCard from "@/components/Common/GCard.vue";

const { isLoading: loadingPreview, zipExplorer, errorMessage, openZip, isZipOpen } = useZipExplorer();

const props = defineProps<{
    zipSource: ArchiveSource;
}>();

async function loadZip() {
    if (!isZipOpen(props.zipSource)) {
        return openZip(props.zipSource);
    }
}

loadZip();
</script>

<template>
    <div class="w-100 d-flex flex-column">
        <div v-if="errorMessage" v-localize class="text-danger">{{ errorMessage }}</div>

        <GCard
            v-if="loadingPreview"
            id="zip-preview-loading-indicator"
            title="Loading archive preview..."
            class="d-flex flex-column align-items-center justify-content-center">
            <template v-slot:description>
                <div class="text-center">
                    <FontAwesomeIcon :icon="faCircleNotch" spin size="2x" />
                </div>
            </template>
        </GCard>
        <div v-else-if="zipExplorer">
            <RoCrateZipView v-if="isRoCrateZip(zipExplorer)" :explorer="zipExplorer" />
            <GalaxyZipView v-else-if="isGalaxyZipExport(zipExplorer)" :explorer="zipExplorer" />
            <RegularZipView v-else-if="zipExplorer" :explorer="zipExplorer" />
        </div>
    </div>
</template>
