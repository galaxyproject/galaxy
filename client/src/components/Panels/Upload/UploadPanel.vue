<script setup lang="ts">
import { BFormCheckbox } from "bootstrap-vue";
import { useRouter } from "vue-router/composables";

import { useUploadAdvancedMode } from "@/composables/upload/uploadAdvancedMode";

import { useUploadState } from "./uploadState";

import UploadMethodList from "./UploadMethodList.vue";
import UploadProgressIndicator from "./UploadProgressIndicator.vue";
import ActivityPanel from "@/components/Panels/ActivityPanel.vue";

const { hasUploads } = useUploadState();
const { advancedMode } = useUploadAdvancedMode();
const router = useRouter();

function showProgressDetails() {
    router.push("/upload/progress");
}
</script>

<template>
    <ActivityPanel title="Import Data" data-description="beta upload panel">
        <template v-slot:header-buttons>
            <BFormCheckbox
                v-model="advancedMode"
                v-b-tooltip.hover.noninteractive
                size="sm"
                switch
                class="mr-2"
                title="Show advanced upload options">
                <span class="small">Advanced</span>
            </BFormCheckbox>
        </template>

        <template v-slot:header>
            <UploadProgressIndicator v-if="hasUploads" @show-details="showProgressDetails" />
            <!-- Search input will be rendered here by UploadMethodList via teleport -->
            <div id="upload-panel-search-slot"></div>
        </template>

        <UploadMethodList :in-panel="true" search-teleport-target="#upload-panel-search-slot" />
    </ActivityPanel>
</template>
