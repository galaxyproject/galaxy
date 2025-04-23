<script setup lang="ts">
import { faCaretDown, faUpload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BDropdown, BDropdownItem, BDropdownText } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed } from "vue";

import { type Plugin } from "@/api/plugins";
import { useToast } from "@/composables/toast";
import { useHistoryStore } from "@/stores/historyStore";
import { uploadPayload } from "@/utils/upload-payload.js";
import { sendPayload } from "@/utils/upload-submit.js";

const { currentHistoryId } = storeToRefs(useHistoryStore());

const toast = useToast();

const props = defineProps<{
    plugin?: Plugin;
}>();

const urlTuples = computed(
    () =>
        props.plugin?.tests
            ?.map((item) => {
                const url = item.param?.name === "dataset_id" ? item.param?.value : null;
                if (url) {
                    const filename = getFilename(url);
                    return filename.trim() ? ([filename, url] as [string, string]) : null;
                }
            })
            .filter((tuple): tuple is [string, string] => Boolean(tuple)) ?? []
);

function getFilename(url: string): string {
    try {
        const pathname = new URL(url).pathname;
        const parts = pathname.split("/").filter(Boolean);
        return parts.length ? parts.pop()! : "";
    } catch {
        return "";
    }
}

function onSubmit(name: string, url: string) {
    try {
        const data = uploadPayload([{ fileMode: "new", fileUri: url }], currentHistoryId.value);
        sendPayload({
            data,
            success: () => toast.success(`The sample dataset '${name}' is being uploaded to your history.`),
            error: () => toast.error(`Uploading the sample dataset '${name}' has failed.`),
        });
    } catch (err) {
        console.log(err);
    }
}
</script>

<template>
    <BDropdown
        v-if="urlTuples.length > 0"
        v-b-tooltip.hover
        no-caret
        right
        role="button"
        title="Versions"
        variant="link"
        aria-label="Select Versions"
        class="tool-versions"
        size="sm">
        <template v-slot:button-content>
            <FontAwesomeIcon :icon="faCaretDown" />
        </template>
        <BDropdownText>
            <small class="font-weight-bold text-primary text-uppercase">Sample Data</small>
        </BDropdownText>
        <BDropdownItem v-for="[name, url] of urlTuples" :key="url" @click="() => onSubmit(name, url)">
            <span>
                <FontAwesomeIcon :icon="faUpload" />
                <span v-localize>{{ name }}</span>
            </span>
        </BDropdownItem>
    </BDropdown>
</template>
