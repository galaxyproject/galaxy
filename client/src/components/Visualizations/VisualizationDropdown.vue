<script setup lang="ts">
import { faCaretDown, faSpinner, faUpload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BDropdown, BDropdownItem, BDropdownText } from "bootstrap-vue";
import { storeToRefs } from "pinia";

import { useToast } from "@/composables/toast";
import { useHistoryStore } from "@/stores/historyStore";
import { uploadPayload } from "@/utils/upload-payload.js";
import { sendPayload } from "@/utils/upload-submit.js";

const { currentHistoryId } = storeToRefs(useHistoryStore());

const toast = useToast();

interface TestType {
    extension: string;
    name: string;
    url: string;
}

defineProps<{
    tests?: Array<TestType>;
}>();

function onSubmit(name: string, url: string) {
    try {
        const data = uploadPayload([{ fileMode: "new", fileUri: url }], currentHistoryId.value);
        sendPayload(data, {
            success: () => toast.success(`The sample dataset '${name}' is being uploaded to your history.`),
            error: () => toast.error(`Uploading the sample dataset '${name}' has failed.`),
        });
    } catch (err) {
        toast.error(`Uploading the sample dataset '${name}' has failed. ${err}`);
        console.error(err);
    }
}
</script>

<template>
    <div v-if="!currentHistoryId" class="d-flex align-items-center h-100">
        <FontAwesomeIcon :icon="faSpinner" spin />
    </div>
    <BDropdown
        v-else-if="tests && tests.length > 0"
        v-b-tooltip.hover
        no-caret
        right
        role="button"
        title="Options"
        variant="link"
        aria-label="Select Options"
        size="sm">
        <template v-slot:button-content>
            <FontAwesomeIcon :icon="faCaretDown" />
        </template>
        <BDropdownText>
            <small class="font-weight-bold text-primary text-uppercase">Upload Sample</small>
        </BDropdownText>
        <BDropdownItem v-for="test of tests" :key="test.url" @click="() => onSubmit(test.name, test.url)">
            <span>
                <FontAwesomeIcon :icon="faUpload" />
                <span v-localize>{{ test.name }}</span>
            </span>
        </BDropdownItem>
    </BDropdown>
</template>
