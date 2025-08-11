<script setup lang="ts">
import { faFolder, faGlobe, faPlus, faUser } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BFormCheckbox, BPagination } from "bootstrap-vue";
import { watch } from "vue";
import { useRouter } from "vue-router";

import type { FilterFileSourcesOptions, RemoteEntry } from "@/api/remoteFiles";
import type { TableField } from "@/components/Common/GTable.types";
import type { SelectionItem } from "@/components/SelectionDialog/selectionTypes";
import type { RemoteFileBrowserMode } from "@/composables/useRemoteFileBrowser";
import { useRemoteFileBrowser } from "@/composables/useRemoteFileBrowser";
import { USER_FILE_PREFIX } from "@/utils/url";

import GButton from "@/components/BaseComponents/GButton.vue";
import BreadcrumbNavigation from "@/components/Common/BreadcrumbNavigation.vue";
import GTable from "@/components/Common/GTable.vue";
import RemoteEntryMetadata from "@/components/Panels/Upload/shared/RemoteEntryMetadata.vue";
import DataDialogSearch from "@/components/SelectionDialog/DataDialogSearch.vue";

interface Props {
    /** Controls which entry types can be selected. */
    mode?: RemoteFileBrowserMode;
    /** Whether multiple entries can be selected simultaneously. */
    multiple?: boolean;
    /** Optional filter to restrict visible file sources. */
    filterOptions?: FilterFileSourcesOptions;
    /** Text displayed on the confirm action button. */
    okText?: string;
    /**
     * When false, the bottom action bar (confirm button) is hidden.
     * Use this when embedding the browser inside a modal that provides its own footer.
     */
    showActions?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    mode: "file",
    multiple: false,
    filterOptions: undefined,
    okText: "Select",
    showActions: true,
});

const emit = defineEmits<{
    /** Emitted when the user confirms their selection. Always an array even for single-select. */
    (e: "confirm", items: SelectionItem[]): void;
    /** Emitted whenever the selection count changes. Useful for parents controlling a modal OK button. */
    (e: "selection-change", count: number): void;
}>();

const router = useRouter();

const browser = useRemoteFileBrowser({
    mode: props.mode,
    multiple: props.multiple,
    filterOptions: props.filterOptions,
});

const {
    urlTracker,
    breadcrumbs,
    navigateToBreadcrumb,
    open,
    browserItems,
    isBusy,
    errorMessage,
    currentPage,
    perPage,
    totalMatches,
    hasPagination,
    searchQuery,
    updateSearchQuery,
    selectionCount,
    isSelected,
    toggleSelection,
    selectableItemsOnCurrentPage,
    allSelectableSelected,
    someSelectableSelected,
    toggleSelectAll,
    getSelectedItems,
} = browser;

// Notify parent whenever selection count changes (used by modal to update OK button state)
watch(selectionCount, (count) => emit("selection-change", count));

const browserFields: TableField[] = [
    {
        key: "select",
        label: "",
        width: "40px",
        align: "center",
    },
    {
        key: "user",
        label: "",
        sortable: false,
        width: "35px",
        align: "center",
    },
    {
        key: "name",
        label: "Name",
        sortable: false,
        align: "center",
    },
    {
        key: "details",
        label: "Details",
        sortable: false,
        align: "left",
    },
];

function onDirectoryClick(item: SelectionItem) {
    if (props.mode === "directory" || props.mode === "any") {
        // In directory/any mode, clicking a directory row toggles its selection;
        // double-clicking (or the icon) is not exposed here — navigate via the name icon only.
        toggleSelection(item);
    } else {
        open(item);
    }
}

function handleRowClick(event: { item: SelectionItem }) {
    if (isBusy.value || errorMessage.value) {
        return;
    }
    const item = event.item;
    if (!item.isLeaf) {
        onDirectoryClick(item);
    } else {
        toggleSelection(item);
    }
}

function navigateInto(item: SelectionItem) {
    if (!item.isLeaf) {
        open(item);
    }
}

function getItemEntry(item: SelectionItem): RemoteEntry {
    return item.entry as unknown as RemoteEntry;
}

function onErrorRetry() {
    errorMessage.value = undefined;
    currentPage.value = 1;
    browser.load();
}

function confirmSelection() {
    emit("confirm", getSelectedItems());
}

function createNewFileSource() {
    router.push("/file_source_instances/create");
}

function isItemSelectable(item: SelectionItem): boolean {
    if (props.mode === "file") {
        return item.isLeaf;
    }
    if (props.mode === "directory") {
        return !item.isLeaf;
    }
    return true; // "any"
}

/** Expose reset and getSelectedItems for parent components (e.g. modal). */
defineExpose({
    reset: browser.reset,
    getSelectedItems,
    selectionCount,
});
</script>

<template>
    <div class="remote-file-browser-content">
        <!-- Navigation breadcrumb -->
        <div class="browser-header mb-2">
            <BreadcrumbNavigation
                v-if="!urlTracker.isAtRoot.value"
                :items="breadcrumbs"
                @navigate="navigateToBreadcrumb" />
            <div v-else>
                <span class="font-weight-bold">Browse a File Source below</span> or
                <GButton color="grey" size="small" @click="createNewFileSource">
                    <FontAwesomeIcon :icon="faPlus" class="mr-1" />
                    Connect New Remote Source
                </GButton>
            </div>
        </div>

        <!-- Search bar -->
        <div class="search-bar-container mb-2">
            <DataDialogSearch
                :value="searchQuery"
                :title="urlTracker.isAtRoot.value ? 'file sources' : 'files and folders'"
                @input="updateSearchQuery" />
        </div>

        <!-- Error message -->
        <BAlert v-if="errorMessage" variant="danger" show dismissible @dismissed="errorMessage = undefined">
            <div class="d-flex justify-content-between align-items-center">
                <span>{{ errorMessage }}</span>
                <GButton color="red" class="ml-2" @click="onErrorRetry">Retry</GButton>
            </div>
        </BAlert>

        <!-- Browser table -->
        <div class="browser-table-container">
            <GTable
                v-if="!errorMessage && (browserItems.length > 0 || isBusy)"
                :items="browserItems"
                :fields="browserFields"
                :overlay-loading="isBusy"
                hover
                striped
                clickable-rows
                compact
                fixed
                class="browser-table"
                @row-click="handleRowClick">
                <!-- Select-all checkbox in header -->
                <template v-slot:head(select)>
                    <BFormCheckbox
                        v-if="!urlTracker.isAtRoot.value && selectableItemsOnCurrentPage.length > 0"
                        :checked="allSelectableSelected"
                        :indeterminate="someSelectableSelected"
                        @change="toggleSelectAll"
                        @click.stop />
                </template>

                <!-- Per-row selection checkbox -->
                <template v-slot:cell(select)="{ item }">
                    <BFormCheckbox
                        v-if="isItemSelectable(item)"
                        :checked="isSelected(item)"
                        @change="toggleSelection(item)"
                        @click.stop />
                </template>

                <!-- Icon column: highlights user-created vs admin file sources -->
                <template v-slot:cell(user)="{ item }">
                    <span
                        v-if="urlTracker.isAtRoot.value && !item.isLeaf && item.url.startsWith(USER_FILE_PREFIX)"
                        v-g-tooltip.hover
                        title="You created this file source">
                        <FontAwesomeIcon :icon="faUser" class="text-primary" fixed-width />
                    </span>
                    <span
                        v-else-if="urlTracker.isAtRoot.value && !item.isLeaf"
                        v-g-tooltip.hover
                        title="This file source was created by an administrator and is globally available">
                        <FontAwesomeIcon :icon="faGlobe" class="text-primary" fixed-width />
                    </span>
                </template>

                <!-- Name column: directory rows have a navigate icon -->
                <template v-slot:cell(name)="{ item }">
                    <div class="d-flex align-items-center">
                        <!-- Folder icon acts as a navigation trigger in all modes -->
                        <button
                            v-if="!item.isLeaf"
                            class="btn btn-link p-0 mr-2 navigate-btn"
                            title="Open directory"
                            @click.stop="navigateInto(item)">
                            <FontAwesomeIcon :icon="faFolder" class="text-warning" fixed-width />
                        </button>
                        <span>{{ item.label }}</span>
                    </div>
                </template>

                <!-- Details column: file metadata or file-source description -->
                <template v-slot:cell(details)="{ item }">
                    <RemoteEntryMetadata v-if="item.isLeaf" :entry="getItemEntry(item)" />
                    <span v-else-if="urlTracker.isAtRoot.value && item.details">
                        {{ item.details }}
                    </span>
                </template>
            </GTable>

            <!-- Empty state -->
            <div v-else-if="!errorMessage && !isBusy" class="text-center text-muted my-5">
                <p v-if="searchQuery" class="lead">
                    No {{ urlTracker.isAtRoot.value ? "file sources" : "files or folders" }} match your search "{{
                        searchQuery
                    }}"
                </p>
                <p v-else-if="urlTracker.isAtRoot.value" class="lead">
                    No file sources available. Connect a new remote source to get started.
                </p>
                <p v-else class="lead">This directory is empty.</p>
            </div>
        </div>

        <!-- Pagination -->
        <div v-if="hasPagination" class="mt-2">
            <BPagination
                v-model="currentPage"
                :total-rows="totalMatches"
                :per-page="perPage"
                align="center"
                size="sm" />
        </div>

        <!-- Action bar (hidden when embedded in a modal with its own footer) -->
        <div v-if="showActions" class="browser-actions mt-3">
            <GButton color="blue" :disabled="selectionCount === 0" @click="confirmSelection">
                <FontAwesomeIcon :icon="faPlus" class="mr-1" />
                {{ okText }} ({{ selectionCount }})
            </GButton>
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "@/style/scss/theme/blue.scss";

.remote-file-browser-content {
    height: 100%;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}

.browser-header {
    flex-shrink: 0;
}

.search-bar-container {
    flex-shrink: 0;
}

.browser-table-container {
    flex: 1;
    overflow: auto;
    min-height: 0;

    :deep(.browser-table thead) {
        position: sticky;
        top: 0;
        z-index: 1;
        background-color: var(--background-color);
    }

    :deep(tbody tr) {
        cursor: pointer;

        &:hover {
            background-color: rgba($brand-primary, 0.05);
        }
    }
}

.browser-actions {
    flex-shrink: 0;
    display: flex;
    gap: 0.5rem;
    padding-top: 1rem;
    border-top: 1px solid $border-color;
}

.navigate-btn {
    color: inherit;
    line-height: 1;
}
</style>
