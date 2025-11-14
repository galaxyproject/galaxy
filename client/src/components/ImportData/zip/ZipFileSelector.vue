<script setup lang="ts">
import { BAlert, BPagination } from "bootstrap-vue";
import { storeToRefs } from "pinia";
import { computed, ref, watch } from "vue";

import { usePagination } from "@/composables/pagination";
import type { ArchiveSource, ImportableFile, ImportableZipContents } from "@/composables/zipExplorer";
import { useUserStore } from "@/stores/userStore";

import DelayedInput from "@/components/Common/DelayedInput.vue";
import Heading from "@/components/Common/Heading.vue";
import ListHeader from "@/components/Common/ListHeader.vue";
import ZipFileEntryCard from "@/components/ImportData/zip/ZipFileEntryCard.vue";

interface Props {
    zipSource: ArchiveSource;
    zipContents: ImportableZipContents;
    selectedItems: ImportableFile[];
    bytesLimit?: number;
}

const props = defineProps<Props>();

const emit = defineEmits<{
    (e: "update:selectedItems", value: ImportableFile[]): void;
}>();

const userStore = useUserStore();
const { isAnonymous } = storeToRefs(userStore);

const localSelectedItems = ref<ImportableFile[]>(props.selectedItems);
const searchQuery = ref("");

function toggleSelection(item: ImportableFile) {
    const index = localSelectedItems.value.findIndex((selected) => selected.path === item.path);
    if (index === -1) {
        localSelectedItems.value.push(item);
    } else {
        localSelectedItems.value.splice(index, 1);
    }
    emit("update:selectedItems", localSelectedItems.value);
}

function matchesSearch(file: ImportableFile): boolean {
    if (!searchQuery.value) {
        return true;
    }
    const query = searchQuery.value.toLowerCase();
    return (
        file.name.toLowerCase().includes(query) ||
        file.path.toLowerCase().includes(query) ||
        Boolean(file.description && file.description.toLowerCase().includes(query))
    );
}

const filteredWorkflows = computed(() => {
    return props.zipContents.workflows.filter(matchesSearch);
});

const filteredFiles = computed(() => {
    return props.zipContents.files.filter(matchesSearch);
});

// Combine workflows and files for unified pagination
const allFilteredItems = computed(() => [...filteredWorkflows.value, ...filteredFiles.value]);

const {
    currentPage,
    itemsPerPage,
    paginatedItems: allPaginatedItems,
    totalItems,
    showPagination,
    onPageChange,
    resetPage,
} = usePagination(allFilteredItems);

// Split paginated items back into workflows and files
const paginatedWorkflows = computed(() => {
    return allPaginatedItems.value.filter((item) => item.type === "workflow");
});

const paginatedFiles = computed(() => {
    return allPaginatedItems.value.filter((item) => item.type === "file");
});

// Reset to page 1 when search changes
watch(searchQuery, resetPage);

const allSelectableFiles = computed(() => [...paginatedWorkflows.value, ...paginatedFiles.value]);

function onSelectAll() {
    const allSelected = allSelectableFiles.value.every((file) =>
        localSelectedItems.value.some((selected) => selected.path === file.path),
    );

    if (allSelected) {
        // Deselect all visible items on current page
        localSelectedItems.value = localSelectedItems.value.filter(
            (selected) => !allSelectableFiles.value.some((file) => file.path === selected.path),
        );
    } else {
        // Select all visible items on current page that aren't already selected
        const newSelections = allSelectableFiles.value.filter(
            (file) => !localSelectedItems.value.some((selected) => selected.path === file.path),
        );
        localSelectedItems.value = [...localSelectedItems.value, ...newSelections];
    }
    emit("update:selectedItems", localSelectedItems.value);
}

const allSelected = computed(() => {
    if (allSelectableFiles.value.length === 0) {
        return false;
    }
    return allSelectableFiles.value.every((file) =>
        localSelectedItems.value.some((selected) => selected.path === file.path),
    );
});

const indeterminateSelected = computed(() => {
    const selectedCount = allSelectableFiles.value.filter((file) =>
        localSelectedItems.value.some((selected) => selected.path === file.path),
    ).length;
    return selectedCount > 0 && selectedCount < allSelectableFiles.value.length;
});

const currentListView = computed(() => userStore.currentListViewPreferences.zipFileSelector || "list");

const localFileSizeLimit = computed(() => {
    return props.zipSource instanceof File ? props.bytesLimit : undefined;
});

function onSearch(value: string) {
    searchQuery.value = value;
}
</script>

<template>
    <div class="zip-file-selector w-100">
        <div class="zip-file-selector-search mb-3">
            <DelayedInput
                :value="searchQuery"
                :delay="200"
                placeholder="Search files by name or path"
                @change="onSearch" />
        </div>

        <ListHeader
            list-id="zipFileSelector"
            show-view-toggle
            show-select-all
            :all-selected="allSelected"
            :indeterminate-selected="indeterminateSelected"
            :select-all-disabled="allSelectableFiles.length === 0"
            @select-all="onSelectAll" />

        <div v-if="paginatedWorkflows.length > 0" class="d-flex flex-column w-100">
            <Heading h3 separator> Workflows </Heading>

            <BAlert v-if="isAnonymous" variant="warning" show fade>You must be logged in to import workflows</BAlert>
            <p>Here you can select workflows compatible with Galaxy and import them into your account.</p>

            <div class="d-flex flex-wrap">
                <ZipFileEntryCard
                    v-for="workflow in paginatedWorkflows"
                    :key="workflow.path"
                    :file="workflow"
                    :grid-view="currentListView === 'grid'"
                    :selected="localSelectedItems.includes(workflow)"
                    @select="toggleSelection(workflow)" />
            </div>
        </div>

        <div v-if="paginatedFiles.length > 0" class="d-flex flex-column w-100">
            <Heading h3 separator> Files </Heading>

            <p>Here you can select individual files to import into your <b>current history</b>.</p>

            <div class="d-flex flex-wrap">
                <ZipFileEntryCard
                    v-for="dataset in paginatedFiles"
                    :key="dataset.path"
                    :file="dataset"
                    :bytes-limit="localFileSizeLimit"
                    :grid-view="currentListView === 'grid'"
                    :selected="localSelectedItems.includes(dataset)"
                    @select="toggleSelection(dataset)" />
            </div>
        </div>

        <BAlert v-if="searchQuery && filteredWorkflows.length === 0 && filteredFiles.length === 0" variant="info" show>
            No files found matching "{{ searchQuery }}". Try a different search term.
        </BAlert>

        <div v-if="showPagination" class="d-flex justify-content-center py-3 mt-3">
            <BPagination
                :value="currentPage"
                :total-rows="totalItems"
                :per-page="itemsPerPage"
                align="center"
                size="sm"
                first-number
                last-number
                @change="onPageChange" />
        </div>
    </div>
</template>
