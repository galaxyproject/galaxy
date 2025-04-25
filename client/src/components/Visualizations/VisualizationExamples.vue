<script setup lang="ts">
import { faFileUpload, faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BDropdown, BDropdownItem, BDropdownText } from "bootstrap-vue";
import { storeToRefs } from "pinia";

import { useToast } from "@/composables/toast";
import { useHistoryStore } from "@/stores/historyStore";
import { uploadPayload } from "@/utils/upload-payload.js";
import { sendPayload } from "@/utils/upload-submit.js";

const { currentHistoryId } = storeToRefs(useHistoryStore());

const toast = useToast();

interface UrlDataType {
    name: string;
    url: string;
}

defineProps<{
    urlData?: Array<UrlDataType>;
}>();

function onSubmit(name: string, url: string) {
    const data = uploadPayload([{ fileMode: "new", fileUri: url }], currentHistoryId.value);
    sendPayload(data, {
        success: () => toast.success(`The sample dataset '${name}' is being uploaded to your history.`),
        error: () => toast.error(`Uploading the sample dataset '${name}' has failed.`),
    });
}
</script>

<template>
    <div v-if="!currentHistoryId" class="d-flex align-items-center h-100">
        <FontAwesomeIcon :icon="faSpinner" spin />
    </div>
    <BDropdown
        v-else-if="urlData && urlData.length > 0"
        v-b-tooltip.hover
        no-caret
        right
        role="button"
        title="Upload Examples"
        variant="link"
        aria-label="Upload Examples"
        size="sm">
        <template v-slot:button-content>
            <FontAwesomeIcon :icon="faFileUpload" />
        </template>
        <BDropdownText>
            <small class="text-primary text-uppercase">Upload Examples</small>
        </BDropdownText>
        <BDropdownItem v-for="ud of urlData" :key="ud.url" @click="() => onSubmit(ud.name, ud.url)">
            <span>
                <FontAwesomeIcon :icon="faFileUpload" />
                <span v-localize>{{ ud.name }}</span>
            </span>
        </BDropdownItem>
    </BDropdown>
</template>
