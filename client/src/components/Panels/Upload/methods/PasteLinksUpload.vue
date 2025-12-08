<script setup lang="ts">
import { computed, ref } from "vue";

import { useUploadQueue } from "@/composables/uploadQueue";

import type { UploadMethodConfig } from "../types";

import GButton from "@/components/BaseComponents/GButton.vue";
import GTip from "@/components/BaseComponents/GTip.vue";

interface Props {
    method: UploadMethodConfig;
    targetHistoryId: string;
}
const props = defineProps<Props>();

const emit = defineEmits<{ (e: "upload-start"): void; (e: "cancel"): void }>();

const uploadQueue = useUploadQueue();

const defaultDbKey = "?";
const defaultExtension = "auto";

const placeholder = "https://example.org/data1.txt\nhttps://example.org/data2.txt";

const selectedExtension = ref<string>(defaultExtension || "auto");
const selectedDbKey = ref<string>(defaultDbKey || "?");
const spaceToTab = ref(false);
const toPosixLines = ref(false);
const deferred = ref(false);

const urlText = ref("");
const urls = computed(() =>
    urlText.value
        .split(/\r?\n/)
        .map((u) => u.trim())
        .filter((u) => u.length),
);
const hasUrls = computed(() => urls.value.length > 0);

function handleCancel() {
    emit("cancel");
}

function handleStartUpload() {
    if (!hasUrls.value) {
        return;
    }

    const uploads = urls.value.map((url) => ({
        uploadMode: "paste-links" as const,
        name: url, // TODO: make file name editable
        size: 0,
        targetHistoryId: props.targetHistoryId,
        dbkey: selectedDbKey.value,
        extension: selectedExtension.value,
        spaceToTab: spaceToTab.value,
        toPosixLines: toPosixLines.value,
        deferred: deferred.value,
        url,
    }));

    uploadQueue.enqueue(uploads);
    urlText.value = "";
    emit("upload-start");
}
</script>

<template>
    <div class="paste-links-upload">
        <GTip tips="Paste one URL per line. Galaxy will fetch each file." class="mb-3" />
        <label for="paste-links-textarea" class="sr-only">Paste URLs</label>
        <textarea
            id="paste-links-textarea"
            v-model="urlText"
            class="form-control mb-2"
            rows="8"
            :placeholder="placeholder"></textarea>
        <div class="metadata-controls small mb-3 text-muted d-flex flex-wrap align-items-center">
            <div class="mr-3">
                <label for="pl-ext" class="mr-1">Type</label>
                <input
                    id="pl-ext"
                    v-model="selectedExtension"
                    class="form-control form-control-sm d-inline-block w-auto"
                    aria-label="Extension" />
            </div>
            <div class="mr-3">
                <label for="pl-dbkey" class="mr-1">DbKey</label>
                <input
                    id="pl-dbkey"
                    v-model="selectedDbKey"
                    class="form-control form-control-sm d-inline-block w-auto"
                    aria-label="DbKey" />
            </div>
            <div class="form-check mr-2">
                <input id="pl-st" v-model="spaceToTab" type="checkbox" class="form-check-input" />
                <label for="pl-st" class="form-check-label">space→tab</label>
            </div>
            <div class="form-check mr-2">
                <input id="pl-pl" v-model="toPosixLines" type="checkbox" class="form-check-input" />
                <label for="pl-pl" class="form-check-label">POSIX lines</label>
            </div>
            <div class="form-check mr-2">
                <input id="pl-def" v-model="deferred" type="checkbox" class="form-check-input" />
                <label for="pl-def" class="form-check-label">Deferred</label>
            </div>
            <div class="ml-auto">
                <span>{{ urls.length }} URL(s)</span>
            </div>
        </div>
        <div class="actions d-flex justify-content-end">
            <GButton outline color="grey" @click="handleCancel">Cancel</GButton>
            <GButton class="ml-2" color="blue" :disabled="!hasUrls" @click="handleStartUpload">Upload</GButton>
        </div>
    </div>
</template>

<style scoped lang="scss">
.paste-links-upload {
    display: flex;
    flex-direction: column;
    height: 100%;
}
textarea {
    font-family: monospace;
}
</style>
