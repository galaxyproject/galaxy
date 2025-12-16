<script setup lang="ts">
import { faExclamationTriangle, faLink, faPlus, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BFormCheckbox, BFormInput, BFormSelect, BTable } from "bootstrap-vue";
import { computed, nextTick, ref, watch } from "vue";

import { findExtension } from "@/components/Upload/utils";
import { useUploadConfigurations } from "@/composables/uploadConfigurations";
import type { CollectionConfig } from "@/composables/uploadQueue";
import { useUploadQueue } from "@/composables/uploadQueue";

import type { UploadMethodComponent, UploadMethodConfig } from "../types";
import type { CollectionCreationState } from "../types/collectionCreation";

import CollectionCreationConfig from "../CollectionCreationConfig.vue";
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
    ext: string;
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

const isReadyToUpload = computed(() => {
    if (!hasItems.value) {
        return false;
    }
    // If collection creation is active, it must be valid to proceed
    if (collectionState.value.validation.isActive && !collectionState.value.validation.isValid) {
        return false;
    }
    return true;
});

watch(isReadyToUpload, (ready) => emit("ready", ready), { immediate: true });

function extractNameFromUrl(url: string): string {
    try {
        const urlObj = new URL(url);
        const pathname = urlObj.pathname;
        const segments = pathname.split("/").filter((s) => s.length > 0);
        if (segments.length > 0) {
            const lastSegment = segments[segments.length - 1];
            if (lastSegment) {
                // Decode URI component to handle encoded characters
                return decodeURIComponent(lastSegment);
            }
        }
    } catch {
        // If URL parsing fails, fall through to return the full URL
    }
    return url;
}

function isValidUrl(url: string): boolean | null {
    if (!url.trim()) {
        return false;
    }
    const hasValidProtocol = url.startsWith("http://") || url.startsWith("https://") || url.startsWith("ftp://");
    return hasValidProtocol ? null : false;
}

function isNameValid(name: string): boolean | null {
    return name.trim().length > 0 ? null : false;
}

function restoreOriginalName(item: UrlItem) {
    if (!item.name.trim()) {
        item.name = extractNameFromUrl(item.url);
    }
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
            ext: defaultExtension,
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

function getExtensionWarning(extensionId: string): string | null {
    const ext = findExtension(effectiveExtensions.value, extensionId);
    return ext?.upload_warning || null;
}

// Bulk operations
const bulkExtension = ref<string | null>(null);
const bulkDbKey = ref<string | null>(null);

const bulkExtensionWarning = computed(() => {
    if (!bulkExtension.value) {
        return null;
    }
    const ext = findExtension(effectiveExtensions.value, bulkExtension.value);
    return ext?.upload_warning || null;
});

function setAllExtensions(extension: string | null) {
    if (extension) {
        urlItems.value.forEach((item) => {
            item.ext = extension;
        });
    }
}

function setAllDbKeys(dbKey: string | null) {
    if (dbKey) {
        urlItems.value.forEach((item) => {
            item.dbkey = dbKey;
        });
    }
}

const allSpaceToTab = computed(() => urlItems.value.length > 0 && urlItems.value.every((f) => f.spaceToTab));

const allToPosixLines = computed(() => urlItems.value.length > 0 && urlItems.value.every((f) => f.toPosixLines));

const allDeferred = computed(() => urlItems.value.length > 0 && urlItems.value.every((f) => f.deferred));

const spaceToTabIndeterminate = computed(
    () =>
        urlItems.value.length > 0 &&
        urlItems.value.some((f) => f.spaceToTab) &&
        !urlItems.value.every((f) => f.spaceToTab),
);

const toPosixLinesIndeterminate = computed(
    () =>
        urlItems.value.length > 0 &&
        urlItems.value.some((f) => f.toPosixLines) &&
        !urlItems.value.every((f) => f.toPosixLines),
);

const deferredIndeterminate = computed(
    () =>
        urlItems.value.length > 0 && urlItems.value.some((f) => f.deferred) && !urlItems.value.every((f) => f.deferred),
);

function toggleAllSpaceToTab() {
    const newValue = !allSpaceToTab.value;
    urlItems.value.forEach((f) => (f.spaceToTab = newValue));
}

function toggleAllToPosixLines() {
    const newValue = !allToPosixLines.value;
    urlItems.value.forEach((f) => (f.toPosixLines = newValue));
}

function toggleAllDeferred() {
    const newValue = !allDeferred.value;
    urlItems.value.forEach((f) => (f.deferred = newValue));
}

// Table configuration
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
        extension: item.ext,
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
                                :title="item.url"
                                class="url-input" />
                            <FontAwesomeIcon
                                v-if="isValidUrl(item.url) === false"
                                v-b-tooltip.hover.noninteractive
                                class="text-warning ml-1 flex-shrink-0"
                                :icon="faExclamationTriangle"
                                title="URL should start with http://, https://, or ftp://" />
                        </div>
                    </template>

                    <!-- Extension column with bulk operations -->
                    <template v-slot:head(extension)>
                        <div class="column-header-vertical">
                            <span class="column-title">Type</span>
                            <BFormSelect
                                v-model="bulkExtension"
                                v-b-tooltip.hover.noninteractive
                                size="sm"
                                title="Set file format for all URLs"
                                :disabled="!configurationsReady"
                                @change="setAllExtensions">
                                <option :value="null">Set all...</option>
                                <option v-for="(ext, extIndex) in effectiveExtensions" :key="extIndex" :value="ext.id">
                                    {{ ext.text }}
                                </option>
                            </BFormSelect>
                            <FontAwesomeIcon
                                v-if="bulkExtensionWarning"
                                v-b-tooltip.hover.noninteractive
                                class="text-warning warning-icon"
                                :icon="faExclamationTriangle"
                                :title="bulkExtensionWarning" />
                        </div>
                    </template>

                    <template v-slot:cell(extension)="{ item }">
                        <div class="d-flex align-items-center">
                            <BFormSelect
                                v-model="item.ext"
                                v-b-tooltip.hover.noninteractive
                                size="sm"
                                title="File format (auto-detect recommended)"
                                :disabled="!configurationsReady">
                                <option v-for="(ext, extIndex) in effectiveExtensions" :key="extIndex" :value="ext.id">
                                    {{ ext.text }}
                                </option>
                            </BFormSelect>
                            <FontAwesomeIcon
                                v-if="getExtensionWarning(item.ext)"
                                v-b-tooltip.hover.noninteractive
                                class="text-warning ml-1 flex-shrink-0"
                                :icon="faExclamationTriangle"
                                :title="getExtensionWarning(item.ext)" />
                        </div>
                    </template>

                    <!-- DbKey column with bulk operations -->
                    <template v-slot:head(dbKey)>
                        <div class="column-header-vertical">
                            <span class="column-title">Reference</span>
                            <BFormSelect
                                v-model="bulkDbKey"
                                v-b-tooltip.hover.noninteractive
                                size="sm"
                                title="Set database key for all URLs"
                                :disabled="!configurationsReady"
                                @change="setAllDbKeys">
                                <option :value="null">Set all...</option>
                                <option v-for="(dbKey, dbKeyIndex) in listDbKeys" :key="dbKeyIndex" :value="dbKey.id">
                                    {{ dbKey.text }}
                                </option>
                            </BFormSelect>
                        </div>
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
                        <div class="options-header">
                            <span class="options-title">Upload Settings</span>
                            <div class="d-flex align-items-center">
                                <BFormCheckbox
                                    v-b-tooltip.hover.noninteractive
                                    :checked="allSpaceToTab"
                                    :indeterminate="spaceToTabIndeterminate"
                                    size="sm"
                                    class="mr-2"
                                    title="Toggle all: Convert spaces to tab characters"
                                    @change="toggleAllSpaceToTab">
                                    <span class="small">Spaces→Tabs</span>
                                </BFormCheckbox>
                                <BFormCheckbox
                                    v-b-tooltip.hover.noninteractive
                                    :checked="allToPosixLines"
                                    :indeterminate="toPosixLinesIndeterminate"
                                    size="sm"
                                    class="mr-2"
                                    title="Toggle all: Convert line endings to POSIX standard"
                                    @change="toggleAllToPosixLines">
                                    <span class="small">POSIX</span>
                                </BFormCheckbox>
                                <BFormCheckbox
                                    v-b-tooltip.hover.noninteractive
                                    :checked="allDeferred"
                                    :indeterminate="deferredIndeterminate"
                                    size="sm"
                                    title="Toggle all: Galaxy will store a reference and fetch data only when needed by a tool"
                                    @change="toggleAllDeferred">
                                    <span class="small">Deferred</span>
                                </BFormCheckbox>
                            </div>
                        </div>
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
    flex-shrink: 0;
    border-bottom: 1px solid $border-color;
    padding-bottom: 0.5rem;
}

.url-table-container {
    flex: 1;
    min-height: 0;
    overflow: auto;

    :deep(.table) {
        table-layout: auto;
        min-width: 100%;
    }

    :deep(.url-table-header) {
        position: sticky;
        top: 0;
        background-color: $white;
        z-index: 100;

        th {
            vertical-align: middle;
            white-space: nowrap;
        }
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

    .column-header-vertical {
        display: flex;
        flex-direction: column;
        align-items: stretch;
        position: relative;

        .column-title {
            font-weight: 600;
            margin-bottom: 0.25rem;
        }

        .warning-icon {
            position: absolute;
            right: 0;
            top: 0;
        }
    }

    .options-header {
        .options-title {
            display: block;
            font-weight: 600;
            margin-bottom: 0.25rem;
        }
    }

    .remove-btn {
        width: 30px;
        display: inline-flex;
        align-items: center;
        justify-content: center;

        &:hover {
            background-color: rgba($brand-danger, 0.1);
        }
    }
}

.url-list-actions {
    flex-shrink: 0;
    display: flex;
    gap: 0.5rem;
    justify-content: flex-start;
    padding-top: 1rem;
    border-top: 1px solid $border-color;
}
</style>
