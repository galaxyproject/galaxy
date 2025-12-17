<script setup lang="ts">
import {
    faChevronDown,
    faChevronRight,
    faExclamationTriangle,
    faPlus,
    faTimes,
} from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BFormCheckbox, BFormInput, BFormSelect, BTable } from "bootstrap-vue";
import { computed, nextTick, ref, watch } from "vue";

import { findExtension } from "@/components/Upload/utils";
import { useUploadConfigurations } from "@/composables/uploadConfigurations";
import type { CollectionConfig } from "@/composables/uploadQueue";
import { useUploadQueue } from "@/composables/uploadQueue";
import { bytesToString } from "@/utils/utils";

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

interface PasteItem {
    id: number;
    name: string;
    content: string;
    extension: string;
    dbkey: string;
    spaceToTab: boolean;
    toPosixLines: boolean;
    _showDetails?: boolean;
}

let nextId = 1;

const pasteItems = ref<PasteItem[]>([
    {
        id: nextId++,
        name: "Pasted Dataset 1",
        content: "",
        extension: configOptions.value?.defaultExtension || "auto",
        dbkey: configOptions.value?.defaultDbKey || "?",
        spaceToTab: false,
        toPosixLines: false,
        _showDetails: true,
    },
]);

const hasItems = computed(() => pasteItems.value.some((item) => item.content.trim().length > 0));

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

function addPasteItem() {
    const newId = nextId++;
    pasteItems.value.push({
        id: newId,
        name: `Pasted Dataset ${pasteItems.value.length + 1}`,
        content: "",
        extension: configOptions.value?.defaultExtension || "auto",
        dbkey: configOptions.value?.defaultDbKey || "?",
        spaceToTab: false,
        toPosixLines: false,
        _showDetails: true,
    });

    scrollToBottom();
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

function getExpandToggleTitle(detailsShowing: boolean): string {
    return detailsShowing ? "Collapse content" : "Expand content";
}

function getExpandAllToggleTitle(allExpanded: boolean): string {
    return allExpanded ? "Collapse all" : "Expand all";
}

function handleCollectionStateChange(state: CollectionCreationState) {
    collectionState.value = state;
}

function isNameValid(name: string): boolean | null {
    return name.trim().length > 0 ? null : false;
}

function restoreOriginalName(item: PasteItem) {
    if (!item.name.trim()) {
        const index = pasteItems.value.findIndex((i) => i.id === item.id);
        item.name = `Pasted Dataset ${index + 1}`;
    }
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
        pasteItems.value.forEach((item) => {
            item.extension = extension;
        });
    }
}

function setAllDbKeys(dbKey: string | null) {
    if (dbKey) {
        pasteItems.value.forEach((item) => {
            item.dbkey = dbKey;
        });
    }
}

const allSpaceToTab = computed(() => pasteItems.value.length > 0 && pasteItems.value.every((f) => f.spaceToTab));

const allToPosixLines = computed(() => pasteItems.value.length > 0 && pasteItems.value.every((f) => f.toPosixLines));

const spaceToTabIndeterminate = computed(
    () =>
        pasteItems.value.length > 0 &&
        pasteItems.value.some((f) => f.spaceToTab) &&
        !pasteItems.value.every((f) => f.spaceToTab),
);

const toPosixLinesIndeterminate = computed(
    () =>
        pasteItems.value.length > 0 &&
        pasteItems.value.some((f) => f.toPosixLines) &&
        !pasteItems.value.every((f) => f.toPosixLines),
);

function toggleAllSpaceToTab() {
    const newValue = !allSpaceToTab.value;
    pasteItems.value.forEach((f) => (f.spaceToTab = newValue));
}

function toggleAllToPosixLines() {
    const newValue = !allToPosixLines.value;
    pasteItems.value.forEach((f) => (f.toPosixLines = newValue));
}

const allExpanded = computed(() => pasteItems.value.length > 0 && pasteItems.value.every((f) => f._showDetails));

function toggleAllExpanded() {
    const newValue = !allExpanded.value;
    pasteItems.value.forEach((f) => (f._showDetails = newValue));
}

// Table configuration
const tableFields = [
    { key: "expand", label: "", sortable: false, tdClass: "text-center align-middle", thStyle: { width: "40px" } },
    {
        key: "name",
        label: "Name",
        sortable: true,
        thStyle: { width: "200px" },
        tdClass: "paste-name-cell align-middle",
    },
    {
        key: "size",
        label: "Size",
        sortable: true,
        thStyle: { minWidth: "80px", width: "80px" },
        tdClass: "align-middle",
    },
    {
        key: "preview",
        label: "Content Preview",
        sortable: false,
        thStyle: {},
        tdClass: "align-middle preview-column",
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

function startUpload() {
    const validItems = pasteItems.value.filter((item) => item.content.trim().length > 0);
    if (validItems.length === 0) {
        return;
    }

    const uploads = validItems.map((item) => ({
        uploadMode: "paste-content" as const,
        name: item.name,
        size: new Blob([item.content]).size,
        targetHistoryId: props.targetHistoryId,
        dbkey: item.dbkey,
        extension: item.extension,
        spaceToTab: item.spaceToTab,
        toPosixLines: item.toPosixLines,
        deferred: false,
        content: item.content,
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

    // Reset to single empty item
    const newId = nextId++;
    pasteItems.value = [
        {
            id: newId,
            name: "Pasted Dataset 1",
            content: "",
            extension: configOptions.value?.defaultExtension || "auto",
            dbkey: configOptions.value?.defaultDbKey || "?",
            spaceToTab: false,
            toPosixLines: false,
        },
    ];
    collectionConfigComponent.value?.reset();
}

defineExpose<UploadMethodComponent>({ startUpload });
</script>

<template>
    <div class="paste-content-upload">
        <div class="paste-list">
            <div class="paste-list-header mb-2">
                <div class="d-flex justify-content-between align-items-center">
                    <span class="font-weight-bold">{{ pasteItems.length }} dataset(s)</span>
                </div>
            </div>

            <div ref="tableContainerRef" class="paste-table-container">
                <BTable
                    :items="pasteItems"
                    :fields="tableFields"
                    hover
                    striped
                    small
                    fixed
                    thead-class="paste-table-header">
                    <!-- Expand toggle column header -->
                    <template v-slot:head(expand)>
                        <button
                            v-b-tooltip.hover.noninteractive
                            class="btn btn-link btn-sm p-0"
                            :title="getExpandAllToggleTitle(allExpanded)"
                            :aria-label="getExpandAllToggleTitle(allExpanded)"
                            @click="toggleAllExpanded">
                            <FontAwesomeIcon :icon="allExpanded ? faChevronDown : faChevronRight" fixed-width />
                        </button>
                    </template>

                    <!-- Expand toggle column -->
                    <template v-slot:cell(expand)="{ toggleDetails, detailsShowing }">
                        <button
                            v-b-tooltip.hover.noninteractive
                            class="btn btn-link btn-sm p-0"
                            :title="getExpandToggleTitle(detailsShowing)"
                            :aria-label="getExpandToggleTitle(detailsShowing)"
                            @click="toggleDetails"
                            @keydown.enter.prevent="toggleDetails"
                            @keydown.space.prevent="toggleDetails">
                            <FontAwesomeIcon :icon="detailsShowing ? faChevronDown : faChevronRight" fixed-width />
                        </button>
                    </template>

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

                    <!-- Size column -->
                    <template v-slot:cell(size)="{ item, toggleDetails }">
                        <span
                            class="clickable-cell"
                            role="button"
                            tabindex="0"
                            @click="toggleDetails"
                            @keydown.enter.prevent="toggleDetails"
                            @keydown.space.prevent="toggleDetails">
                            {{ getItemSize(item.content) }}
                        </span>
                    </template>

                    <!-- Preview column -->
                    <template v-slot:cell(preview)="{ item, toggleDetails }">
                        <div
                            class="clickable-cell"
                            role="button"
                            tabindex="0"
                            @click="toggleDetails"
                            @keydown.enter.prevent="toggleDetails"
                            @keydown.space.prevent="toggleDetails">
                            <div v-if="item.content" class="preview-text">
                                <span class="text-muted small font-italic">
                                    {{ item.content }}
                                </span>
                            </div>
                            <span
                                v-else-if="!item.content"
                                v-b-tooltip.hover.noninteractive
                                title="This dataset is empty and will be skipped during upload."
                                class="small font-italic text-danger">
                                No content
                            </span>
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
                                title="Set file format for all datasets"
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
                                v-if="getExtensionWarning(item.extension)"
                                v-b-tooltip.hover.noninteractive
                                class="text-warning ml-1 flex-shrink-0"
                                :icon="faExclamationTriangle"
                                :title="getExtensionWarning(item.extension)" />
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
                                title="Set database key for all datasets"
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
                                    title="Toggle all: Convert line endings to POSIX standard"
                                    @change="toggleAllToPosixLines">
                                    <span class="small">POSIX</span>
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
                                title="Convert line endings to POSIX standard">
                                <span class="small">POSIX</span>
                            </BFormCheckbox>
                        </div>
                    </template>

                    <!-- Actions column -->
                    <template v-slot:cell(actions)="{ item }">
                        <button
                            v-b-tooltip.hover.noninteractive
                            class="btn btn-link text-danger remove-btn"
                            title="Remove dataset from list"
                            @click="removeItem(item.id)">
                            <FontAwesomeIcon :icon="faTimes" />
                        </button>
                    </template>

                    <!-- Row details for textarea -->
                    <template v-slot:row-details="{ item }">
                        <div class="paste-content-row">
                            <label :for="`paste-content-${item.id}`" class="sr-only">
                                Paste data for {{ item.name }}
                            </label>
                            <textarea
                                :id="`paste-content-${item.id}`"
                                v-model="item.content"
                                class="form-control paste-textarea"
                                rows="6"
                                placeholder="Paste your data here"
                                @keydown.stop></textarea>
                        </div>
                    </template>
                </BTable>
            </div>

            <!-- Collection Creation Section -->
            <CollectionCreationConfig
                ref="collectionConfigComponent"
                :files="pasteItems"
                @update:state="handleCollectionStateChange" />

            <div class="paste-list-actions mt-2">
                <GButton
                    color="grey"
                    tooltip
                    tooltip-placement="top"
                    title="Add another dataset to paste content into"
                    @click="addPasteItem">
                    <FontAwesomeIcon :icon="faPlus" class="mr-1" />
                    Add Another Dataset
                </GButton>
            </div>
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "@/style/scss/theme/blue.scss";

.paste-content-upload {
    height: 100%;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}

.paste-list {
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    min-height: 0;
}

.paste-list-header {
    flex-shrink: 0;
    border-bottom: 1px solid $border-color;
    padding-bottom: 0.5rem;
}

.paste-table-container {
    flex: 1;
    min-height: 0;
    overflow: auto;

    :deep(.table) {
        table-layout: auto;
        min-width: 100%;
    }

    :deep(.paste-table-header) {
        position: sticky;
        top: 0;
        background-color: $white;
        z-index: 100;

        th {
            vertical-align: middle;
            white-space: nowrap;
        }
    }

    :deep(.paste-name-cell) {
        min-width: 200px;
    }

    :deep(.preview-column) {
        width: 100%;
        max-width: 300px;
        overflow: hidden;
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

    .size-preview {
        display: flex;
        align-items: center;

        .preview-text {
            color: $text-muted;
            font-style: italic;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
    }

    .clickable-cell {
        cursor: pointer;
        user-select: none;
        display: block;
        width: 100%;
        height: 100%;
        padding: 0.25rem;
        margin: -0.25rem;

        .preview-text {
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
    }
}

.paste-content-row {
    padding: 1rem;
    background-color: $gray-100;

    .paste-textarea {
        font-family: monospace;
        font-size: 0.9rem;
        width: 100%;
        border: 1px solid $border-color;
        border-radius: $border-radius-base;

        &:focus {
            border-color: $brand-primary;
            box-shadow: 0 0 0 0.2rem rgba($brand-primary, 0.25);
        }
    }
}

.paste-list-actions {
    flex-shrink: 0;
    display: flex;
    gap: 0.5rem;
    justify-content: flex-start;
    padding-top: 1rem;
    border-top: 1px solid $border-color;
}
</style>
