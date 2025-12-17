<script setup lang="ts">
import { faExclamationTriangle, faLink, faPlus, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BFormCheckbox, BFormInput, BFormSelect, BTable } from "bootstrap-vue";
import { computed, nextTick, ref, watch } from "vue";

import { useBulkUploadOperations } from "@/composables/upload/bulkUploadOperations";
import { useUploadItemValidation } from "@/composables/upload/uploadItemValidation";
import { useUploadReadyState } from "@/composables/upload/uploadReadyState";
import { useUploadConfigurations } from "@/composables/uploadConfigurations";
import type { CollectionConfig } from "@/composables/uploadQueue";
import { useUploadQueue } from "@/composables/uploadQueue";
import { extractNameFromUrl, isValidUrl, validateUrl } from "@/utils/url";

import type { UploadMethodComponent, UploadMethodConfig } from "../types";
import type { CollectionCreationState } from "../types/collectionCreation";

import CollectionCreationConfig from "../CollectionCreationConfig.vue";
import UploadTableBulkDbKeyHeader from "../shared/UploadTableBulkDbKeyHeader.vue";
import UploadTableBulkExtensionHeader from "../shared/UploadTableBulkExtensionHeader.vue";
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

const {
    configOptions,
    effectiveExtensions,
    listDbKeys,
    ready: configurationsReady,
} = useUploadConfigurations(undefined);

const collectionConfigComponent = ref<InstanceType<typeof CollectionCreationConfig> | null>(null);
const collectionState = ref<CollectionCreationState>({
    config: null,
    validation: {
        isValid: true,
        isActive: false,
        message: "",
    },
});

const tableContainerRef = ref<HTMLElement | null>(null);

interface UrlItem {
    id: number;
    url: string;
    name: string;
    extension: string;
    dbkey: string;
    spaceToTab: boolean;
    toPosixLines: boolean;
    deferred: boolean;
}

let nextId = 1;

const urlItems = ref<UrlItem[]>([]);
const urlText = ref("");
const showInputArea = ref(true);

const placeholder = "https://example.org/data1.txt\nhttps://example.org/data2.txt";

const hasItems = computed(() => urlItems.value.length > 0);

const { isNameValid, restoreOriginalName: restoreOriginalNameBase } = useUploadItemValidation();

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

function restoreOriginalName(item: UrlItem) {
    restoreOriginalNameBase(item, extractNameFromUrl(item.url));
}

function addUrlsFromText() {
    if (!urlText.value.trim()) {
        return;
    }

    const urls = urlText.value
        .split(/\r?\n/)
        .map((u) => u.trim())
        .filter((u) => u.length > 0);

    const defaultExtension = configOptions.value?.defaultExtension || "auto";
    const defaultDbKey = configOptions.value?.defaultDbKey || "?";

    for (const url of urls) {
        urlItems.value.push({
            id: nextId++,
            url,
            name: extractNameFromUrl(url),
            extension: defaultExtension,
            dbkey: defaultDbKey,
            spaceToTab: false,
            toPosixLines: false,
            deferred: false,
        });
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

function handleCollectionStateChange(state: CollectionCreationState) {
    collectionState.value = state;
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
    collectionConfigComponent.value?.reset();
}

function startUpload() {
    const validItems = urlItems.value.filter((item) => item.url.trim().length > 0);
    if (validItems.length === 0) {
        return;
    }

    const uploads = validItems.map((item) => ({
        uploadMode: "paste-links" as const,
        name: item.name,
        size: 0,
        targetHistoryId: props.targetHistoryId,
        dbkey: item.dbkey,
        extension: item.extension,
        spaceToTab: item.spaceToTab,
        toPosixLines: item.toPosixLines,
        deferred: item.deferred,
        url: item.url,
    }));

    const fullCollectionConfig: CollectionConfig | undefined = collectionState.value.config
        ? {
              name: collectionState.value.config.name,
              type: collectionState.value.config.type,
              hideSourceItems: true,
              historyId: props.targetHistoryId,
          }
        : undefined;

    uploadQueue.enqueue(uploads, fullCollectionConfig);

    // Reset state
    urlItems.value = [];
    urlText.value = "";
    showInputArea.value = true;
    collectionConfigComponent.value?.reset();
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
                        <BFormInput
                            v-model="item.name"
                            v-b-tooltip.hover.noninteractive
                            size="sm"
                            :state="isNameValid(item.name)"
                            title="Dataset name in your history (required)"
                            @blur="restoreOriginalName(item)" />
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
                            :model-value="bulk.bulkExtension.value"
                            :extensions="effectiveExtensions"
                            :warning="bulk.bulkExtensionWarning.value"
                            :disabled="!configurationsReady"
                            tooltip="Set file format for all URLs"
                            @update:model-value="bulk.setAllExtensions" />
                    </template>

                    <template v-slot:cell(extension)="{ item }">
                        <div class="d-flex align-items-center">
                            <BFormSelect
                                v-model="item.extension"
                                v-b-tooltip.hover.noninteractive
                                size="sm"
                                title="File format (auto-detect recommended)"
                                :disabled="!configurationsReady">
                                <option v-for="(ext, extIndex) in effectiveExtensions" :key="extIndex" :value="ext.id">
                                    {{ ext.text }}
                                </option>
                            </BFormSelect>
                            <FontAwesomeIcon
                                v-if="bulk.getExtensionWarning(item.extension)"
                                v-b-tooltip.hover.noninteractive
                                class="text-warning ml-1 flex-shrink-0"
                                :icon="faExclamationTriangle"
                                :title="bulk.getExtensionWarning(item.extension)" />
                        </div>
                    </template>

                    <!-- DbKey column with bulk operations -->
                    <template v-slot:head(dbKey)>
                        <UploadTableBulkDbKeyHeader
                            :model-value="bulk.bulkDbKey.value"
                            :db-keys="listDbKeys"
                            :disabled="!configurationsReady"
                            tooltip="Set database key for all URLs"
                            @update:model-value="bulk.setAllDbKeys" />
                    </template>

                    <template v-slot:cell(dbKey)="{ item }">
                        <BFormSelect
                            v-model="item.dbkey"
                            v-b-tooltip.hover.noninteractive
                            size="sm"
                            title="Database key for this dataset"
                            :disabled="!configurationsReady">
                            <option v-for="(dbKey, dbKeyIndex) in listDbKeys" :key="dbKeyIndex" :value="dbKey.id">
                                {{ dbKey.text }}
                            </option>
                        </BFormSelect>
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
                        <div class="d-flex align-items-center">
                            <BFormCheckbox
                                v-model="item.spaceToTab"
                                v-b-tooltip.hover.noninteractive
                                size="sm"
                                class="mr-2"
                                title="Convert spaces to tab characters">
                                <span class="small">Spaces→Tabs</span>
                            </BFormCheckbox>
                            <BFormCheckbox
                                v-model="item.toPosixLines"
                                v-b-tooltip.hover.noninteractive
                                size="sm"
                                class="mr-2"
                                title="Convert line endings to POSIX standard">
                                <span class="small">POSIX</span>
                            </BFormCheckbox>
                            <BFormCheckbox
                                v-model="item.deferred"
                                v-b-tooltip.hover.noninteractive
                                size="sm"
                                title="Galaxy will store a reference and fetch data only when needed by a tool">
                                <span class="small">Deferred</span>
                            </BFormCheckbox>
                        </div>
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
