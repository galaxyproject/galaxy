<script setup lang="ts">
import { faLink, faPlus, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BFormInput, BTable } from "bootstrap-vue";
import { computed, nextTick, onMounted, ref, watch } from "vue";

import { useBulkUploadOperations } from "@/composables/upload/bulkUploadOperations";
import { useCollectionCreation } from "@/composables/upload/collectionCreation";
import { useUploadDefaults } from "@/composables/upload/uploadDefaults";
import { useUploadItemValidation } from "@/composables/upload/uploadItemValidation";
import { useUploadReadyState } from "@/composables/upload/uploadReadyState";
import { useUploadQueue } from "@/composables/uploadQueue";
import { useUploadStagingStore } from "@/stores/uploadStagingStore";
import { mapToPasteUrlUpload } from "@/utils/upload/itemMappers";
import { extractNameFromUrl, isValidUrl, validateUrl } from "@/utils/url";

import type { UploadMethodComponent, UploadMethodConfig } from "../types";
import type { PasteUrlItem } from "../types/uploadItem";

import CollectionCreationConfig from "../CollectionCreationConfig.vue";
import UploadTableBulkDbKeyHeader from "../shared/UploadTableBulkDbKeyHeader.vue";
import UploadTableBulkExtensionHeader from "../shared/UploadTableBulkExtensionHeader.vue";
import UploadTableDbKeyCell from "../shared/UploadTableDbKeyCell.vue";
import UploadTableExtensionCell from "../shared/UploadTableExtensionCell.vue";
import UploadTableNameCell from "../shared/UploadTableNameCell.vue";
import UploadTableOptionsCell from "../shared/UploadTableOptionsCell.vue";
import UploadTableOptionsHeader from "../shared/UploadTableOptionsHeader.vue";
import GButton from "@/components/BaseComponents/GButton.vue";

interface Props {
    method: UploadMethodConfig;
    targetHistoryId: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "ready", ready: boolean): void;
}>();

const uploadQueue = useUploadQueue();

const { effectiveExtensions, listDbKeys, configurationsReady, createItemDefaults } = useUploadDefaults();

const tableContainerRef = ref<HTMLElement | null>(null);
const collectionConfigComponent = ref<InstanceType<typeof CollectionCreationConfig> | null>(null);
const stagingStore = useUploadStagingStore();

const { collectionState, handleCollectionStateChange, buildCollectionConfig, resetCollection } =
    useCollectionCreation(collectionConfigComponent);

let nextId = 1;

function createPasteUrlItem(id: number, url: string, name: string): PasteUrlItem {
    return {
        id,
        url,
        name,
        ...createItemDefaults(),
        deferred: false,
    };
}

const urlItems = ref<PasteUrlItem[]>([]);
const urlText = ref("");
const showInputArea = ref(true);

onMounted(() => {
    const staged = stagingStore.getItems<PasteUrlItem>(props.method.id);
    if (staged.length) {
        urlItems.value = staged;
        nextId = Math.max(...staged.map((i) => i.id)) + 1;
        showInputArea.value = false;
    }
});

watch(
    urlItems,
    (items) => {
        stagingStore.setItems(props.method.id, items);
    },
    { deep: true },
);

const placeholder = "https://example.org/data1.txt\nhttps://example.org/data2.txt";

const hasItems = computed(() => urlItems.value.length > 0);

const { isNameValid, restoreOriginalName } = useUploadItemValidation();

const bulk = useBulkUploadOperations(urlItems, effectiveExtensions);

// Additional validation for URL items
const hasInvalidUrls = computed(() => urlItems.value.some((item) => !isValidUrl(item.url)));

const { isReadyToUpload } = useUploadReadyState(
    hasItems,
    collectionState,
    computed(() => !hasInvalidUrls.value),
);

watch(isReadyToUpload, (ready) => emit("ready", ready), { immediate: true });

function getUrlValidationMessage(url: string): string {
    return validateUrl(url).message || url;
}

function addUrlsFromText() {
    if (!urlText.value.trim()) {
        return;
    }

    const urls = urlText.value
        .split(/\r?\n/)
        .map((u) => u.trim())
        .filter((u) => u.length > 0);

    for (const url of urls) {
        urlItems.value.push(createPasteUrlItem(nextId++, url, extractNameFromUrl(url)));
    }

    urlText.value = "";
    showInputArea.value = false;
    scrollToBottom();
}

function showUrlInput() {
    showInputArea.value = true;
}

function scrollToBottom() {
    nextTick(() => {
        if (tableContainerRef.value) {
            const container = tableContainerRef.value;
            container.scrollTop = container.scrollHeight;
        }
    });
}

function removeItem(id: number) {
    urlItems.value = urlItems.value.filter((item) => item.id !== id);
}

const tableFields = [
    {
        key: "name",
        label: "Name",
        sortable: true,
        thStyle: { width: "200px" },
        tdClass: "url-name-cell align-middle",
    },
    {
        key: "url",
        label: "URL",
        sortable: false,
        thStyle: { width: "auto" },
        tdClass: "align-middle url-column",
    },
    {
        key: "extension",
        label: "Type",
        sortable: false,
        thStyle: { minWidth: "180px", width: "180px" },
        tdClass: "align-middle",
    },
    {
        key: "dbKey",
        label: "Reference",
        sortable: false,
        thStyle: { minWidth: "200px", width: "200px" },
        tdClass: "align-middle",
    },
    {
        key: "options",
        label: "Upload Settings",
        sortable: false,
        thStyle: { width: "auto" },
        tdClass: "align-middle",
    },
    { key: "actions", label: "", sortable: false, tdClass: "text-right align-middle", thStyle: { width: "50px" } },
];

function clearAll() {
    urlItems.value = [];
    urlText.value = "";
    showInputArea.value = true;
    resetCollection();
}

function startUpload() {
    const validItems = urlItems.value.filter((item) => item.url.trim().length > 0);
    if (validItems.length === 0) {
        return;
    }

    const uploads = validItems.map((item) => mapToPasteUrlUpload(item, props.targetHistoryId));
    const collectionConfig = buildCollectionConfig(props.targetHistoryId);

    uploadQueue.enqueue(uploads, collectionConfig);

    // Reset state
    urlItems.value = [];
    stagingStore.clearItems(props.method.id);
    urlText.value = "";
    showInputArea.value = true;
    resetCollection();
}

defineExpose<UploadMethodComponent>({ startUpload });
</script>

<template>
    <div class="paste-links-upload">
        <!-- URL Input Area -->
        <div v-if="showInputArea" class="url-input-area">
            <label for="paste-links-textarea" class="font-weight-bold mb-2">Paste URLs</label>
            <textarea
                id="paste-links-textarea"
                v-model="urlText"
                class="form-control mb-2 url-textarea"
                rows="8"
                :placeholder="placeholder"></textarea>
            <div class="d-flex justify-content-between align-items-center">
                <span class="text-muted small">One URL per line</span>
                <GButton color="blue" :disabled="!urlText.trim()" @click="addUrlsFromText">
                    <FontAwesomeIcon :icon="faLink" class="mr-1" />
                    Add URLs
                </GButton>
            </div>
        </div>

        <!-- URL Table with Metadata Editing -->
        <div v-else class="url-list">
            <div class="url-list-header mb-2">
                <div class="d-flex justify-content-between align-items-center">
                    <span class="font-weight-bold">{{ urlItems.length }} URL(s) added</span>
                </div>
            </div>

            <div ref="tableContainerRef" class="url-table-container">
                <BTable
                    :items="urlItems"
                    :fields="tableFields"
                    hover
                    striped
                    small
                    fixed
                    thead-class="url-table-header">
                    <!-- Name column -->
                    <template v-slot:cell(name)="{ item }">
                        <UploadTableNameCell
                            :value="item.name"
                            :state="isNameValid(item.name)"
                            @input="item.name = $event"
                            @blur="restoreOriginalName(item, extractNameFromUrl(item.url))" />
                    </template>

                    <!-- URL column -->
                    <template v-slot:cell(url)="{ item }">
                        <div class="d-flex align-items-center">
                            <BFormInput
                                v-model="item.url"
                                v-b-tooltip.hover.noninteractive
                                size="sm"
                                :state="isValidUrl(item.url)"
                                :title="getUrlValidationMessage(item.url)"
                                class="url-input" />
                        </div>
                    </template>

                    <!-- Extension column with bulk operations -->
                    <template v-slot:head(extension)>
                        <UploadTableBulkExtensionHeader
                            :value="bulk.bulkExtension.value"
                            :extensions="effectiveExtensions"
                            :warning="bulk.bulkExtensionWarning.value"
                            :disabled="!configurationsReady"
                            tooltip="Set file format for all URLs"
                            @input="bulk.setAllExtensions" />
                    </template>

                    <template v-slot:cell(extension)="{ item }">
                        <UploadTableExtensionCell
                            :value="item.extension"
                            :extensions="effectiveExtensions"
                            :warning="bulk.getExtensionWarning(item.extension)"
                            :disabled="!configurationsReady"
                            @input="item.extension = $event" />
                    </template>

                    <!-- DbKey column with bulk operations -->
                    <template v-slot:head(dbKey)>
                        <UploadTableBulkDbKeyHeader
                            :value="bulk.bulkDbKey.value"
                            :db-keys="listDbKeys"
                            :disabled="!configurationsReady"
                            tooltip="Set database key for all URLs"
                            @input="bulk.setAllDbKeys" />
                    </template>

                    <template v-slot:cell(dbKey)="{ item }">
                        <UploadTableDbKeyCell
                            :value="item.dbkey"
                            :db-keys="listDbKeys"
                            :disabled="!configurationsReady"
                            @input="item.dbkey = $event" />
                    </template>

                    <!-- Options column with bulk checkboxes -->
                    <template v-slot:head(options)>
                        <UploadTableOptionsHeader
                            :all-space-to-tab="bulk.allSpaceToTab.value"
                            :space-to-tab-indeterminate="bulk.spaceToTabIndeterminate.value"
                            :all-to-posix-lines="bulk.allToPosixLines.value"
                            :to-posix-lines-indeterminate="bulk.toPosixLinesIndeterminate.value"
                            :show-deferred="true"
                            :all-deferred="bulk.allDeferred.value"
                            :deferred-indeterminate="bulk.deferredIndeterminate.value"
                            @toggle-space-to-tab="bulk.toggleAllSpaceToTab"
                            @toggle-to-posix-lines="bulk.toggleAllToPosixLines"
                            @toggle-deferred="bulk.toggleAllDeferred" />
                    </template>

                    <template v-slot:cell(options)="{ item }">
                        <UploadTableOptionsCell
                            :space-to-tab="item.spaceToTab"
                            :to-posix-lines="item.toPosixLines"
                            :deferred="item.deferred"
                            :show-deferred="true"
                            @updateSpaceToTab="item.spaceToTab = $event"
                            @updateToPosixLines="item.toPosixLines = $event"
                            @updateDeferred="item.deferred = $event" />
                    </template>

                    <!-- Actions column -->
                    <template v-slot:cell(actions)="{ item }">
                        <button
                            v-b-tooltip.hover.noninteractive
                            class="btn btn-link text-danger remove-btn"
                            title="Remove URL from list"
                            @click="removeItem(item.id)">
                            <FontAwesomeIcon :icon="faTimes" />
                        </button>
                    </template>
                </BTable>
            </div>

            <!-- Collection Creation Section -->
            <CollectionCreationConfig
                ref="collectionConfigComponent"
                :files="urlItems"
                @update:state="handleCollectionStateChange" />

            <div class="url-list-actions mt-2">
                <GButton
                    color="grey"
                    tooltip
                    tooltip-placement="top"
                    title="Add more URLs to the upload list"
                    @click="showUrlInput">
                    <FontAwesomeIcon :icon="faPlus" class="mr-1" />
                    Add More URLs
                </GButton>
                <GButton
                    outline
                    color="grey"
                    tooltip
                    tooltip-placement="top"
                    title="Remove all URLs from the upload list"
                    @click="clearAll">
                    Clear All
                </GButton>
            </div>
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "@/style/scss/theme/blue.scss";
@import "../shared/upload-table-shared.scss";

.paste-links-upload {
    height: 100%;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}

.url-input-area {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    min-height: 0;

    .url-textarea {
        font-family: monospace;
        font-size: 0.9rem;
        flex: 1;
        resize: none;
    }
}

.url-list {
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    min-height: 0;
}

.url-list-header {
    @include upload-list-header;
}

.url-table-container {
    @include upload-table-container;

    :deep(.url-table-header) {
        @include upload-table-header;
    }

    :deep(.url-name-cell) {
        min-width: 200px;
    }

    :deep(.url-column) {
        width: 100%;
        max-width: 400px;
        overflow: hidden;

        .url-input {
            font-family: monospace;
            font-size: 0.85rem;
        }
    }
}

.url-list-actions {
    @include upload-list-actions;
}
</style>
