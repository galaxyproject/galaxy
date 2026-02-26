<script setup lang="ts">
import { faChevronDown, faChevronRight, faPlus, faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { computed, nextTick, onMounted, ref, watch } from "vue";

import type { TableField } from "@/components/Common/GTable.types";
import { useBulkUploadOperations } from "@/composables/upload/bulkUploadOperations";
import { useCollectionCreation } from "@/composables/upload/collectionCreation";
import { useUploadAdvancedMode } from "@/composables/upload/uploadAdvancedMode";
import { useUploadDefaults } from "@/composables/upload/uploadDefaults";
import { useUploadItemValidation } from "@/composables/upload/uploadItemValidation";
import { useUploadReadyState } from "@/composables/upload/uploadReadyState";
import { useUploadStaging } from "@/composables/upload/useUploadStaging";
import { useUploadQueue } from "@/composables/uploadQueue";
import { mapToPasteContentUpload } from "@/utils/upload/itemMappers";
import { bytesToString } from "@/utils/utils";

import type { UploadMethodComponent, UploadMethodConfig } from "../types";
import type { PasteContentItem } from "../types/uploadItem";

import CollectionCreationConfig from "../CollectionCreationConfig.vue";
import UploadTableBulkDbKeyHeader from "../shared/UploadTableBulkDbKeyHeader.vue";
import UploadTableBulkExtensionHeader from "../shared/UploadTableBulkExtensionHeader.vue";
import UploadTableDbKeyCell from "../shared/UploadTableDbKeyCell.vue";
import UploadTableExtensionCell from "../shared/UploadTableExtensionCell.vue";
import UploadTableNameCell from "../shared/UploadTableNameCell.vue";
import UploadTableOptionsCell from "../shared/UploadTableOptionsCell.vue";
import UploadTableOptionsHeader from "../shared/UploadTableOptionsHeader.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import GTable from "@/components/Common/GTable.vue";

interface Props {
    method: UploadMethodConfig;
    targetHistoryId: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "ready", ready: boolean): void;
}>();

const { advancedMode } = useUploadAdvancedMode();

const uploadQueue = useUploadQueue();

const { effectiveExtensions, listDbKeys, configurationsReady, createItemDefaults } = useUploadDefaults();

const tableContainerRef = ref<HTMLElement | null>(null);
const collectionConfigComponent = ref<InstanceType<typeof CollectionCreationConfig> | null>(null);

const { collectionState, handleCollectionStateChange, buildCollectionConfig, resetCollection } =
    useCollectionCreation(collectionConfigComponent);

let nextId = 1;

function createPasteContentItem(id: number, name: string): PasteContentItem {
    return {
        id,
        name,
        content: "",
        ...createItemDefaults(),
    };
}

const pasteItems = ref<PasteContentItem[]>([createPasteContentItem(nextId++, "Pasted Dataset 1")]);
const expandedItemIds = ref<Set<number>>(new Set());
const rowToggleMap = ref<Map<number, () => void>>(new Map());
const { clear: clearStaging } = useUploadStaging<PasteContentItem>(props.method.id, pasteItems);

const hasItems = computed(() => pasteItems.value.some((item) => item.content.trim().length > 0));

const { isNameValid, restoreOriginalName } = useUploadItemValidation();

const bulk = useBulkUploadOperations(pasteItems, effectiveExtensions);

const { isReadyToUpload } = useUploadReadyState(hasItems, collectionState);

watch(isReadyToUpload, (ready) => emit("ready", ready), { immediate: true });

function addPasteItem() {
    const newId = nextId++;
    pasteItems.value.push(createPasteContentItem(newId, `Pasted Dataset ${pasteItems.value.length + 1}`));
    scrollToBottom();
    nextTick(() => expandRow(newId));
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
    rowToggleMap.value.delete(id);
    const nextExpanded = new Set(expandedItemIds.value);
    nextExpanded.delete(id);
    expandedItemIds.value = nextExpanded;
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

const allExpanded = computed(
    () => pasteItems.value.length > 0 && pasteItems.value.every((item) => expandedItemIds.value.has(item.id)),
);

function registerRowToggle(itemId: number, toggleDetails: () => void) {
    rowToggleMap.value.set(itemId, toggleDetails);
    return "";
}

function isExpanded(itemId: number) {
    return expandedItemIds.value.has(itemId);
}

function setExpanded(itemId: number, expanded: boolean) {
    const nextExpanded = new Set(expandedItemIds.value);
    if (expanded) {
        nextExpanded.add(itemId);
    } else {
        nextExpanded.delete(itemId);
    }
    expandedItemIds.value = nextExpanded;
}

function expandRow(itemId: number) {
    if (isExpanded(itemId)) {
        return;
    }
    const toggle = rowToggleMap.value.get(itemId);
    if (!toggle) {
        return;
    }
    setExpanded(itemId, true);
    toggle();
}

function collapseRow(itemId: number) {
    if (!isExpanded(itemId)) {
        return;
    }
    const toggle = rowToggleMap.value.get(itemId);
    if (!toggle) {
        return;
    }
    setExpanded(itemId, false);
    toggle();
}

function toggleRow(item: PasteContentItem, toggleDetails: () => void) {
    const shouldExpand = !isExpanded(item.id);
    setExpanded(item.id, shouldExpand);
    toggleDetails();
}

function toggleAllExpanded() {
    const shouldExpand = !allExpanded.value;
    pasteItems.value.forEach((item) => {
        if (shouldExpand) {
            expandRow(item.id);
        } else {
            collapseRow(item.id);
        }
    });
}

// Table configuration
const tableFields: TableField[] = [
    {
        key: "expand",
        label: "",
        sortable: false,
        width: "40px",
        align: "center",
    },
    {
        key: "name",
        label: "Name",
        sortable: true,
        width: "200px",
        class: "paste-name-cell",
    },
    {
        key: "size",
        label: "Size",
        sortable: true,
        width: "80px",
    },
    {
        key: "preview",
        label: "Content Preview",
        sortable: false,
        align: "center",
        class: "preview-column",
    },
    {
        key: "extension",
        label: "Type",
        sortable: false,
        width: "180px",
        align: "center",
    },
    {
        key: "dbKey",
        label: "Reference",
        sortable: false,
        width: "200px",
        align: "center",
        class: "reference-column",
    },
    {
        key: "options",
        label: "Upload Settings",
        sortable: false,
        align: "center",
    },
    {
        key: "actions",
        label: "",
        sortable: false,
        width: "50px",
        align: "center",
    },
];

onMounted(() => {
    nextTick(() => {
        pasteItems.value.forEach((item) => expandRow(item.id));
    });
});

function startUpload() {
    const validItems = pasteItems.value.filter((item) => item.content.trim().length > 0);
    if (validItems.length === 0) {
        return;
    }

    const uploads = validItems.map((item) => mapToPasteContentUpload(item, props.targetHistoryId));
    const collectionConfig = buildCollectionConfig(props.targetHistoryId);

    uploadQueue.enqueue(uploads, collectionConfig);

    // Reset to single empty item
    const newItemId = nextId++;
    pasteItems.value = [createPasteContentItem(newItemId, "Pasted Dataset 1")];
    rowToggleMap.value = new Map();
    expandedItemIds.value = new Set();
    nextTick(() => expandRow(newItemId));
    clearStaging();
    resetCollection();
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
                <GTable hover compact fixed stripped :items="pasteItems" :fields="tableFields" class="paste-table">
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
                    <template v-slot:cell(expand)="{ item, toggleDetails }">
                        <span class="sr-only">{{ registerRowToggle(item.id, toggleDetails) }}</span>
                        <button
                            v-b-tooltip.hover.noninteractive
                            class="btn btn-link btn-sm p-0"
                            :title="getExpandToggleTitle(isExpanded(item.id))"
                            :aria-label="getExpandToggleTitle(isExpanded(item.id))"
                            @click="toggleRow(item, toggleDetails)"
                            @keydown.enter.prevent="toggleRow(item, toggleDetails)"
                            @keydown.space.prevent="toggleRow(item, toggleDetails)">
                            <FontAwesomeIcon :icon="isExpanded(item.id) ? faChevronDown : faChevronRight" fixed-width />
                        </button>
                    </template>

                    <!-- Name column -->
                    <template v-slot:cell(name)="{ item, index }">
                        <UploadTableNameCell
                            :value="item.name"
                            :state="isNameValid(item.name)"
                            tooltip="Dataset name in your history (required)"
                            @input="item.name = $event"
                            @blur="restoreOriginalName(item, `Pasted Dataset ${index + 1}`)" />
                    </template>

                    <!-- Size column -->
                    <template v-slot:cell(size)="{ item, toggleDetails }">
                        <span
                            class="clickable-cell"
                            role="button"
                            tabindex="0"
                            @click="toggleRow(item, toggleDetails)"
                            @keydown.enter.prevent="toggleRow(item, toggleDetails)"
                            @keydown.space.prevent="toggleRow(item, toggleDetails)">
                            {{ getItemSize(item.content) }}
                        </span>
                    </template>

                    <!-- Preview column -->
                    <template v-slot:cell(preview)="{ item, toggleDetails }">
                        <div
                            class="clickable-cell"
                            role="button"
                            tabindex="0"
                            @click="toggleRow(item, toggleDetails)"
                            @keydown.enter.prevent="toggleRow(item, toggleDetails)"
                            @keydown.space.prevent="toggleRow(item, toggleDetails)">
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
                        <UploadTableBulkExtensionHeader
                            :value="bulk.bulkExtension.value"
                            :extensions="effectiveExtensions"
                            :warning="bulk.bulkExtensionWarning.value"
                            :disabled="!configurationsReady"
                            tooltip="Set file format for all datasets"
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
                            tooltip="Set database key for all datasets"
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
                            :show-posix="advancedMode"
                            :all-to-posix-lines="bulk.allToPosixLines.value"
                            :to-posix-lines-indeterminate="bulk.toPosixLinesIndeterminate.value"
                            @toggle-space-to-tab="bulk.toggleAllSpaceToTab"
                            @toggle-to-posix-lines="bulk.toggleAllToPosixLines" />
                    </template>

                    <template v-slot:cell(options)="{ item }">
                        <UploadTableOptionsCell
                            :space-to-tab="item.spaceToTab"
                            :show-posix="advancedMode"
                            :to-posix-lines="item.toPosixLines"
                            @updateSpaceToTab="item.spaceToTab = $event"
                            @updateToPosixLines="item.toPosixLines = $event" />
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
                </GTable>
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
@import "../shared/upload-table-shared.scss";

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
    @include upload-list-header;
}

.paste-table-container {
    @include upload-table-container;

    :deep(.paste-table thead) {
        @include upload-table-header;
    }

    :deep(.paste-name-cell) {
        min-width: 200px;
    }

    :deep(.preview-column) {
        width: 100%;
        max-width: 300px;
        overflow: hidden;
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
    @include upload-list-actions;
}
</style>
