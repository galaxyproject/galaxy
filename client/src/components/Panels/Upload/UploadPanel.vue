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
        <template v-slot:activity-panel-header-top>
            <h2 id="activity-panel-heading" class="activity-panel-heading h-sm d-inline-flex align-items-center">
                <span>Import Data</span>
                <span
                    v-b-tooltip.hover.noninteractive
                    class="badge badge-warning ml-2"
                    title="This upload experience is in Beta and is intended to gather user feedback.">
                    Beta
                </span>
            </h2>
        </template>
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
