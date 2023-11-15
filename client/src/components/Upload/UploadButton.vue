<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faUpload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, onMounted, onUnmounted, ref } from "vue";

import { eventHub } from "@/components/plugins/eventHub.js";
import { useGlobalUploadModal } from "@/composables/globalUploadModal";
import localize from "@/utils/localization";
import Query from "@/utils/query-string-parsing";

library.add(faUpload);

const props = withDefaults(
    defineProps<{
        title?: string;
    }>(),
    {
        title: "Download from URL or upload files from disk",
    }
);

const { openGlobalUploadModal } = useGlobalUploadModal();

const status = ref("");
const percentage = ref(0);

onMounted(() => {
    eventHub.$on("upload:status", setStatus);
    eventHub.$on("upload:percentage", setPercentage);
    if (Query.get("tool_id") == "upload1") {
        openGlobalUploadModal();
    }
});

onUnmounted(() => {
    eventHub.$off("upload:status", setStatus);
    eventHub.$off("upload:percentage", setPercentage);
});

const localizedTitle = computed(() => {
    return localize(props.title);
});
function setStatus(val: string) {
    status.value = val;
}

function setPercentage(val: number) {
    percentage.value = val;
}

function showUploadDialog() {
    openGlobalUploadModal();
}
</script>
<template>
    <b-button
        id="activity-upload"
        v-b-tooltip.hover.noninteractive.bottom
        :aria-label="localizedTitle"
        :title="localizedTitle"
        class="upload-button"
        size="sm"
        @click="showUploadDialog">
        <div class="progress">
            <div
                class="progress-bar progress-bar-notransition"
                :class="`progress-bar-${status}`"
                :style="{
                    width: `${percentage}%`,
                }" />
        </div>
        <span class="position-relative">
            <FontAwesomeIcon icon="upload" class="mr-1" />
            <b v-localize>Upload Data</b>
        </span>
    </b-button>
</template>
