<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faUpload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { storeToRefs } from "pinia";
import { computed, onMounted } from "vue";

import { useGlobalUploadModal } from "@/composables/globalUploadModal";
import { useUploadStore } from "@/stores/uploadStore";
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
const { percentage, status } = storeToRefs(useUploadStore());

onMounted(() => {
    if (Query.get("tool_id") == "upload1") {
        openGlobalUploadModal();
    }
});

const localizedTitle = computed(() => {
    return localize(props.title);
});
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
