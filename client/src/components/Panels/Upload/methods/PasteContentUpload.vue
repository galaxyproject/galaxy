<script setup lang="ts">
import { faPlus, faTrash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, onMounted, ref } from "vue";

import { useDatatypeStore } from "@/stores/datatypeStore";
import { useDbKeyStore } from "@/stores/dbKeyStore";
import { bytesToString } from "@/utils/utils";

import type { UploadMethodConfig } from "../types";
import { useUploadService } from "../uploadService";

import GButton from "@/components/BaseComponents/GButton.vue";
import GTip from "@/components/BaseComponents/GTip.vue";
import UploadSelect from "@/components/Upload/UploadSelect.vue";
import UploadSelectExtension from "@/components/Upload/UploadSelectExtension.vue";

interface Props {
    method: UploadMethodConfig;
    targetHistoryId: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{ (e: "upload-start"): void; (e: "cancel"): void }>();

const uploadService = useUploadService();
const dbKeyStore = useDbKeyStore();
const datatypeStore = useDatatypeStore();

const defaultDbKey = "?";
const defaultExtension = "auto";

onMounted(async () => {
    await Promise.all([dbKeyStore.fetchUploadDbKeys(), datatypeStore.fetchUploadDatatypes()]);
});

interface PasteItem {
    id: number;
    name: string;
    content: string;
    ext: string;
    dbkey: string;
    spaceToTab: boolean;
    toPosixLines: boolean;
}

let nextId = 1;

const pasteItems = ref<PasteItem[]>([
    {
        id: nextId++,
        name: "Pasted Dataset 1",
        content: "",
        ext: defaultExtension,
        dbkey: defaultDbKey,
        spaceToTab: false,
        toPosixLines: false,
    },
]);

const hasItems = computed(() => pasteItems.value.some((item) => item.content.trim().length > 0));

function addPasteItem() {
    pasteItems.value.push({
        id: nextId++,
        name: `Pasted Dataset ${pasteItems.value.length + 1}`,
        content: "",
        ext: defaultExtension,
        dbkey: defaultDbKey,
        spaceToTab: false,
        toPosixLines: false,
    });
}

function removeItem(id: number) {
    if (pasteItems.value.length === 1) {
        // Keep at least one item but clear it
        const firstItem = pasteItems.value[0];
        if (firstItem) {
            firstItem.content = "";
            firstItem.name = "Pasted Dataset 1";
        }
        return;
    }
    pasteItems.value = pasteItems.value.filter((item) => item.id !== id);
}

function getItemSize(content: string) {
    return bytesToString(new Blob([content]).size);
}

function updateItemExt(item: PasteItem, newValue: string) {
    item.ext = newValue;
}

function updateItemDbKey(item: PasteItem, newValue: string) {
    item.dbkey = newValue;
}

function handleCancel() {
    emit("cancel");
}

function handleStartUpload() {
    const validItems = pasteItems.value.filter((item) => item.content.trim().length > 0);
    if (validItems.length === 0) {
        return;
    }

    const uploads = validItems.map((item) => ({
        uploadMode: "paste-content" as const,
        name: item.name,
        size: item.content.length,
        targetHistoryId: props.targetHistoryId,
        dbkey: item.dbkey,
        extension: item.ext,
        spaceToTab: item.spaceToTab,
        toPosixLines: item.toPosixLines,
        deferred: false,
        content: item.content,
    }));

    uploadService.enqueue(uploads);

    // Reset to single empty item
    pasteItems.value = [
        {
            id: nextId++,
            name: "Pasted Dataset 1",
            content: "",
            ext: defaultExtension,
            dbkey: defaultDbKey,
            spaceToTab: false,
            toPosixLines: false,
        },
    ];

    emit("upload-start");
}
</script>

<template>
    <div class="paste-content-upload">
        <GTip
            tips="Paste text data for one or more datasets. Add multiple items to import several files at once."
            class="mb-3" />

        <div class="paste-content-area">
            <div class="paste-items-container">
                <div v-for="item in pasteItems" :key="item.id" class="paste-item mb-3">
                    <div class="paste-item-header d-flex align-items-center flex-wrap mb-2">
                        <label :for="`paste-name-${item.id}`" class="mb-0 mr-2 small">Name:</label>
                        <input
                            :id="`paste-name-${item.id}`"
                            v-model="item.name"
                            type="text"
                            class="form-control form-control-sm mr-3 paste-name-input"
                            placeholder="Dataset name"
                            aria-label="Dataset name" />

                        <span class="mr-2 small">Type:</span>
                        <UploadSelectExtension
                            class="mr-3"
                            :value="item.ext"
                            :list-extensions="datatypeStore.getUploadDatatypes"
                            @input="updateItemExt(item, $event)" />

                        <span class="mr-2 small">Reference:</span>
                        <UploadSelect
                            class="mr-3"
                            :value="item.dbkey"
                            :options="dbKeyStore.getUploadDbKeys"
                            what="reference"
                            placeholder="Select Reference"
                            @input="updateItemDbKey(item, $event)" />

                        <label class="mb-0 mr-2 d-flex align-items-center">
                            <input v-model="item.spaceToTab" type="checkbox" class="mr-1" />
                            <span class="small">space→tab</span>
                        </label>
                        <label class="mb-0 mr-2 d-flex align-items-center">
                            <input v-model="item.toPosixLines" type="checkbox" class="mr-1" />
                            <span class="small">POSIX lines</span>
                        </label>

                        <button
                            v-if="pasteItems.length > 1"
                            type="button"
                            class="btn btn-sm btn-link text-danger ml-auto"
                            :aria-label="`Remove ${item.name}`"
                            @click="removeItem(item.id)">
                            <FontAwesomeIcon :icon="faTrash" />
                        </button>
                    </div>

                    <label :for="`paste-content-${item.id}`" class="sr-only">Paste data for {{ item.name }}</label>
                    <textarea
                        :id="`paste-content-${item.id}`"
                        v-model="item.content"
                        class="form-control mb-2"
                        rows="6"
                        placeholder="Paste your data here"></textarea>

                    <div class="small text-muted text-right">
                        {{ getItemSize(item.content) }}
                    </div>
                </div>
            </div>

            <div class="add-section d-flex justify-content-between align-items-center">
                <GButton outline color="grey" @click="addPasteItem">
                    <FontAwesomeIcon :icon="faPlus" class="mr-1" />
                    Add Another Dataset
                </GButton>
                <span class="text-muted small">{{ pasteItems.length }} dataset(s)</span>
            </div>
        </div>

        <div class="actions d-flex justify-content-end">
            <GButton outline color="grey" @click="handleCancel">Cancel</GButton>
            <GButton class="ml-2" color="blue" :disabled="!hasItems" @click="handleStartUpload">Upload</GButton>
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "@/style/scss/theme/blue.scss";

.paste-content-upload {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-height: 0;
}

.paste-content-area {
    flex: 1;
    display: flex;
    flex-direction: column;
    min-height: 0;
    overflow: hidden;
}

.paste-items-container {
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
    min-height: 0;
}

.add-section {
    flex-shrink: 0;
    padding: 1rem 0;
    border-top: 1px solid $border-color;
}

.paste-item {
    padding: 1rem;
    border: 1px solid $border-color;
    border-radius: $border-radius-base;
    background-color: $white;

    &:hover {
        border-color: lighten($brand-primary, 20%);
    }
}

.paste-item-header {
    .paste-name-input {
        max-width: 200px;
    }
}

textarea {
    font-family: monospace;
    font-size: 0.9rem;
}

.actions {
    flex-shrink: 0;
    border-top: 1px solid $border-color;
    padding-top: 1rem;
}
</style>
