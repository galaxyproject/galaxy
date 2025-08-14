<script setup lang="ts">
/**
 * HistoryList Component
 *
 * This component provides a comprehensive interface for managing and viewing histories.
 * Supports multiple views including "My Histories", "Shared Histories", "Published Histories",
 * and "Archived Histories" with features like:
 *
 * - Filtering and searching histories with advanced filter options
 * - Pagination for large history collections
 * - Bulk operations (delete, restore, add tags)
 * - Individual history selection and management
 * - View mode switching (grid/list)
 * - Sorting capabilities
 *
 * @component HistoryList
 * @example
 * <HistoryList activeList="my" />
 * <HistoryList activeList="shared" />
 */

import { faPlus, faTags, faTrash, faTrashRestore } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton, BNav, BNavItem, BOverlay, BPagination } from "bootstrap-vue";
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router/composables";

import {
    type AnyHistoryEntry,
    getArchivedHistories,
    getMyHistories,
    getPublishedHistories,
    getSharedHistories,
} from "@/api/histories";
import { useConfirmDialog } from "@/composables/confirmDialog";
import { Toast } from "@/composables/toast";
import { useHistoryStore } from "@/stores/historyStore";
import { updateHistoryFields } from "@/stores/services/history.services";
import { useUserStore } from "@/stores/userStore";
import { errorMessageAsString } from "@/utils/simple-error";

import { getHistoryListFilters } from "./historyList";

import GButton from "@/components/BaseComponents/GButton.vue";
import GLink from "@/components/BaseComponents/GLink.vue";
import BreadcrumbHeading from "@/components/Common/BreadcrumbHeading.vue";
import FilterMenu from "@/components/Common/FilterMenu.vue";
import Heading from "@/components/Common/Heading.vue";
import ListHeader from "@/components/Common/ListHeader.vue";
import LoginRequired from "@/components/Common/LoginRequired.vue";
import TagsSelectionDialog from "@/components/Common/TagsSelectionDialog.vue";
import HistoryCardList from "@/components/History/HistoryCardList.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

/**
 * Represents a selected history item with minimal required data
 * @typedef {Object} SelectedHistory
 * @property {string} id - The unique identifier of the history
 * @property {string} name - The display name of the history
 * @property {boolean} published - Whether the history is published publicly
 */
type SelectedHistory = {
    id: string;
    name: string;
    published: boolean;
};

interface Props {
    /**
     * The active list view for the history list.
     * Can be "my", "shared", "published", or "archived".
     */
    activeList?: "my" | "shared" | "published" | "archived";
}

const props = withDefaults(defineProps<Props>(), {
    activeList: "my",
});

const breadcrumbItems = [{ title: "Histories", to: "/histories/list" }];

const router = useRouter();
const userStore = useUserStore();
const historyStore = useHistoryStore();
const { confirm } = useConfirmDialog();

const limit = ref(24);
const offset = ref(0);
const loading = ref(true);
const overlay = ref(false);
const filterText = ref("");
const totalHistories = ref(0);
const showAdvanced = ref(false);
const listHeader = ref<typeof ListHeader | null>(null);
const showBulkAddTagsModal = ref(false);
const bulkTagsLoading = ref(false);
const bulkDeleteOrRestoreLoading = ref(false);
const historiesLoaded = ref<AnyHistoryEntry[]>([]);
const selectedHistoryIds = ref<SelectedHistory[]>([]);

/** Computed property that determines if the current view is "My Histories" */
const myView = computed(() => props.activeList === "my");
/** Computed property that determines if the current view is "Shared Histories" */
const sharedView = computed(() => props.activeList === "shared");
/** Computed property that determines if the current view is "Published Histories" */
const publishedView = computed(() => props.activeList === "published");
/** Computed property that determines if the current view is "Archived Histories" */
const archivedView = computed(() => props.activeList === "archived");

/**
 * Dynamic search placeholder text based on the current active list view
 * @returns {string} Contextual placeholder text for the search input
 */
const searchPlaceHolder = computed(() => {
    let placeHolder = "Search my histories";

    if (sharedView.value) {
        placeHolder = "Search shared histories";
    }
    if (publishedView.value) {
        placeHolder = "Search published histories";
    }
    if (archivedView.value) {
        placeHolder = "Search archived histories";
    }

    placeHolder += " by query or use the advanced filtering options";

    return placeHolder;
});

const showDeleted = computed(() => filterText.value.includes("is:deleted"));
const currentPage = computed(() => Math.floor(offset.value / limit.value) + 1);
const currentListViewMode = computed(() => userStore.currentListViewPreferences.histories || "grid");
const sortDesc = computed(() => (listHeader.value && listHeader.value.sortDesc) ?? true);
const sortBy = computed(() => (listHeader.value && listHeader.value.sortBy) || "update_time");
const noItems = computed(() => !loading.value && historiesLoaded.value.length === 0 && !filterText.value);
const noResults = computed(() => !loading.value && historiesLoaded.value.length === 0 && Boolean(filterText.value));
const deleteButtonTitle = computed(() => (showDeleted.value ? "Hide deleted histories" : "Show deleted histories"));

const historyListFilters = computed(() => getHistoryListFilters(props.activeList));
const rawFilters = computed(() =>
    Object.fromEntries(historyListFilters.value.getFiltersForText(filterText.value, true, false))
);
const validFilters = computed(() => historyListFilters.value.getValidFilters(rawFilters.value, true).validFilters);
const invalidFilters = computed(() => historyListFilters.value.getValidFilters(rawFilters.value, true).invalidFilters);
const isSurroundedByQuotes = computed(() => /^["'].*["']$/.test(filterText.value));
const hasInvalidFilters = computed(() => !isSurroundedByQuotes.value && Object.keys(invalidFilters.value).length > 0);

/**
 * Updates a specific filter value in the current filter text
 * @param {string} filterKey - The key of the filter to update
 * @param {any} newValue - The new value for the filter
 */
function updateFilterValue(filterKey: string, newValue: any) {
    const currentFilterText = filterText.value;
    filterText.value = historyListFilters.value.setFilterValue(currentFilterText, filterKey, newValue);
}

/**
 * Toggles the "deleted" filter to show or hide deleted histories
 */
function onToggleDeleted() {
    updateFilterValue("deleted", true);
}

/**
 * Loads histories based on current view (my, shared, published, or archived)
 * @param {boolean} overlayLoading - Whether to show overlay loading instead of full loading
 * @param {boolean} silent - Whether to skip loading indicators
 */
async function load(overlayLoading = false, silent = false) {
    if (!silent) {
        if (overlayLoading) {
            overlay.value = true;
        } else {
            loading.value = true;
        }
    }

    if (hasInvalidFilters.value) {
        overlay.value = false;
        loading.value = false;
        return;
    }

    const options = {
        limit: limit.value,
        offset: offset.value,
        search: validatedFilterText(),
        sortBy: sortBy.value,
        sortDesc: sortDesc.value,
    };

    try {
        if (myView.value) {
            const { data, total } = await getMyHistories(options);

            historiesLoaded.value = data;
            totalHistories.value = total;
        } else if (sharedView.value) {
            const { data, total } = await getSharedHistories(options);

            historiesLoaded.value = data;
            totalHistories.value = total;
        } else if (publishedView.value) {
            const { data, total } = await getPublishedHistories(options);

            historiesLoaded.value = data;
            totalHistories.value = total;
        } else if (archivedView.value) {
            const { data, total } = await getArchivedHistories(options);

            historiesLoaded.value = data;
            totalHistories.value = total;
        }
    } catch (error) {
        Toast.error(`Failed to load histories: ${errorMessageAsString(error)}`);
    } finally {
        loading.value = false;
        overlay.value = false;
    }
}

/**
 * Handles pagination by updating offset and reloading histories
 * @param {number} page - The page number to navigate to
 */
async function onPageChange(page: number) {
    offset.value = (page - 1) * limit.value;
    await load(true);
}

/**
 * Validates and processes filter text, handling quoted strings and filter validation
 * @returns {string} The processed filter text
 */
function validatedFilterText() {
    if (isSurroundedByQuotes.value) {
        // the `filterText` is surrounded by quotes, remove them
        return filterText.value.slice(1, -1);
    } else if (Object.keys(rawFilters.value).length === 0) {
        // there are no filters derived from the `filterText`
        return filterText.value;
    }
    // there are valid filters derived from the `filterText`
    return historyListFilters.value.getFilterText(validFilters.value, true);
}

/**
 * Toggles selection of a specific history item
 * @param {SelectedHistory} h - The history object to toggle selection for
 */
function onSelectHistory(h: SelectedHistory) {
    const index = selectedHistoryIds.value.findIndex((selected) => selected.id === h.id);

    if (index === -1) {
        selectedHistoryIds.value.push(h);
    } else {
        selectedHistoryIds.value.splice(index, 1);
    }
}

/**
 * Toggles selection of all histories in the current view
 * If all are selected, deselects all; otherwise selects all loaded histories
 */
function onSelectAllHistories() {
    if (selectedHistoryIds.value.length === historiesLoaded.value.length) {
        selectedHistoryIds.value = [];
    } else {
        selectedHistoryIds.value = historiesLoaded.value.map((h) => ({
            id: h.id,
            name: h.name,
            published: h.published,
        }));
    }
}

/**
 * Handles bulk deletion of selected histories
 * Shows confirmation dialog and processes deletion with proper error handling
 */
async function onBulkDelete() {
    const totalSelected = selectedHistoryIds.value.length;
    const hasPublished = selectedHistoryIds.value.some((h) => h.published);

    const confirmed = await confirm(
        `${hasPublished ? "Some of the selected histories are published and will be removed from public view. " : ""}
            Are you sure you want to delete ${totalSelected} histories?`,
        {
            id: "bulk-delete-histories",
            title: "Delete histories",
            okTitle: "Delete histories",
            okVariant: "danger",
            cancelVariant: "outline-primary",
            centered: true,
        }
    );

    if (confirmed) {
        const tmpSelected = [...selectedHistoryIds.value];

        try {
            overlay.value = true;
            bulkDeleteOrRestoreLoading.value = true;

            for (const h of selectedHistoryIds.value) {
                await historyStore.deleteHistory(String(h.id));

                tmpSelected.splice(
                    tmpSelected.findIndex((ts) => ts.id === h.id),
                    1
                );
            }

            Toast.success(`Deleted ${totalSelected} histories.`);

            selectedHistoryIds.value = [];
        } catch (e) {
            Toast.error(`Failed to delete some histories.`);
        } finally {
            bulkDeleteOrRestoreLoading.value = false;

            selectedHistoryIds.value = tmpSelected;

            await load(true);
        }
    }
}

/**
 * Handles bulk restoration of selected deleted histories
 * Shows confirmation dialog and processes restoration with proper error handling
 */
async function onBulkRestore() {
    const totalSelected = selectedHistoryIds.value.length;

    const confirmed = await confirm(`Are you sure you want to restore ${totalSelected} histories?`, {
        id: "bulk-restore-histories",
        title: "Restore histories",
        okTitle: "Restore histories",
        okVariant: "primary",
        cancelVariant: "outline-primary",
        centered: true,
    });

    if (confirmed) {
        const tmpSelected = [...selectedHistoryIds.value];

        try {
            overlay.value = true;
            bulkDeleteOrRestoreLoading.value = true;

            for (const his of selectedHistoryIds.value) {
                await historyStore.restoreHistory(his.id);

                tmpSelected.splice(
                    tmpSelected.findIndex((ts) => ts.id === his.id),
                    1
                );
            }

            Toast.success(`Restored ${totalSelected} histories.`);

            selectedHistoryIds.value = [];
        } catch (e) {
            Toast.error(`Failed to restore some histories.`);
        } finally {
            bulkDeleteOrRestoreLoading.value = false;

            selectedHistoryIds.value = tmpSelected;

            await load(true);
        }
    }
}

/**
 * Toggles the visibility of the bulk tags modal
 */
function onToggleBulkTags() {
    showBulkAddTagsModal.value = !showBulkAddTagsModal.value;
}

/**
 * Adds tags to all selected histories
 * @param {string[]} tags - Array of tag strings to add to the selected histories
 */
async function onBulkTagsAdd(tags: string[]) {
    const tmpSelected = [...selectedHistoryIds.value];
    const totalSelected = selectedHistoryIds.value.length;

    try {
        overlay.value = true;
        bulkTagsLoading.value = true;

        for (const his of selectedHistoryIds.value) {
            const prevTags = historiesLoaded.value.find((hl) => hl.id === his.id)?.tags || [];

            await updateHistoryFields(his.id, { tags: [...new Set([...prevTags, ...tags])] });

            tmpSelected.splice(
                tmpSelected.findIndex((ts) => ts.id === his.id),
                1
            );
        }

        Toast.success(`Added tag(s) to ${totalSelected} histories.`);
    } catch (e) {
        Toast.error(`Failed to add tag(s) to some histories. ${e}`);
    } finally {
        bulkTagsLoading.value = false;

        selectedHistoryIds.value = tmpSelected;

        await load(true);
    }
}

/**
 * Watches for changes in filter text, sort options, and sort direction
 * to reload the history list with updated parameters
 */
watch([filterText, sortBy, sortDesc], async () => {
    offset.value = 0;

    selectedHistoryIds.value = [];

    await load(true);
});

onMounted(async () => {
    if (router.currentRoute.query.owner) {
        updateFilterValue("user", `'${router.currentRoute.query.owner}'`);
    }

    await load();
});
</script>

<template>
    <div id="history-list" class="overflow-auto d-flex flex-column">
        <div id="history-list-header" class="mb-2">
            <BreadcrumbHeading :items="breadcrumbItems">
                <GButton
                    v-if="!userStore.isAnonymous"
                    size="small"
                    color="blue"
                    outline
                    to="/histories/import"
                    data-description="grid action import new history">
                    <FontAwesomeIcon :icon="faPlus" />
                    Import History
                </GButton>
            </BreadcrumbHeading>

            <BNav pills justified class="mb-2">
                <BNavItem id="histories-my-tab" :active="myView" :disabled="userStore.isAnonymous" to="/histories/list">
                    My Histories
                    <LoginRequired
                        v-if="userStore.isAnonymous"
                        target="histories-my-tab"
                        title="Manage your Histories" />
                </BNavItem>
                <BNavItem
                    id="histories-shared-tab"
                    :active="sharedView"
                    :disabled="userStore.isAnonymous"
                    to="/histories/list_shared">
                    Histories Shared with Me
                    <LoginRequired
                        v-if="userStore.isAnonymous"
                        target="histories-shared-tab"
                        title="View Shared Histories" />
                </BNavItem>
                <BNavItem
                    id="histories-published-tab"
                    :active="publishedView"
                    :disabled="userStore.isAnonymous"
                    to="/histories/list_published">
                    Public Histories
                    <LoginRequired
                        v-if="userStore.isAnonymous"
                        target="histories-published-tab"
                        title="View Published Histories" />
                </BNavItem>
                <BNavItem
                    id="histories-archived-tab"
                    :active="archivedView"
                    :disabled="userStore.isAnonymous"
                    to="/histories/archived">
                    Archived Histories
                    <LoginRequired
                        v-if="userStore.isAnonymous"
                        target="histories-archived-tab"
                        title="View Archived Histories" />
                </BNavItem>
            </BNav>

            <FilterMenu
                id="history-list-filter"
                name="history-list-filter"
                :filter-class="historyListFilters"
                :filter-text.sync="filterText"
                :loading="loading || overlay"
                view="compact"
                :placeholder="searchPlaceHolder"
                :show-advanced.sync="showAdvanced" />

            <ListHeader
                ref="listHeader"
                list-id="histories"
                show-sort-options
                show-view-toggle
                :show-select-all="myView"
                :select-all-disabled="loading || overlay || noItems || noResults"
                :all-selected="!!selectedHistoryIds.length && selectedHistoryIds.length === historiesLoaded.length"
                :indeterminate-selected="
                    selectedHistoryIds.length > 0 && selectedHistoryIds.length < historiesLoaded.length
                "
                @select-all="onSelectAllHistories">
                <template v-slot:extra-filter>
                    <div v-if="activeList === 'my'">
                        Filter:
                        <BButton
                            id="show-deleted"
                            v-b-tooltip.hover
                            size="sm"
                            :title="deleteButtonTitle"
                            :pressed="showDeleted"
                            variant="outline-primary"
                            @click="onToggleDeleted">
                            <FontAwesomeIcon :icon="faTrash" fixed-width />
                            Show deleted
                        </BButton>
                    </div>
                </template>
            </ListHeader>
        </div>

        <div v-if="loading" class="h-100">
            <BAlert variant="info" show>
                <LoadingSpan message="Loading histories" />
            </BAlert>
        </div>
        <div v-else-if="!loading && !overlay && noItems" class="h-100">
            <BAlert id="history-list-empty" variant="info" show>
                No histories found. You may create or import new histories using the buttons above.
            </BAlert>
        </div>
        <span v-else-if="!loading && !overlay && (noResults || hasInvalidFilters)" class="h-100">
            <BAlert v-if="!hasInvalidFilters" id="no-history-found" variant="info" show>
                No histories found matching: <span class="font-weight-bold">{{ filterText }}</span>
            </BAlert>

            <BAlert v-else id="no-history-found-invalid" variant="danger" show>
                <Heading h4 inline size="sm" class="flex-grow-1 mb-2">Invalid filters in query:</Heading>
                <ul>
                    <li v-for="[invalidKey, value] in Object.entries(invalidFilters)" :key="invalidKey">
                        <b>{{ invalidKey }}</b>
                        : {{ value }}
                    </li>
                </ul>
                <GLink @click="filterText = validatedFilterText()"> Remove invalid filters from query </GLink>
                or
                <GLink
                    title="Note that this might produce inaccurate results"
                    tooltip
                    @click="filterText = `'${filterText}'`">
                    Match the exact query provided
                </GLink>
            </BAlert>
        </span>
        <BOverlay
            v-else
            id="history-list-overlay"
            :show="overlay"
            class="h-100 d-flex flex-column history-list-overlay"
            rounded="sm">
            <HistoryCardList
                :histories="historiesLoaded"
                :shared-view="sharedView"
                :published-view="publishedView"
                :archived-view="archivedView"
                :grid-view="currentListViewMode === 'grid'"
                :selectable="myView"
                :selected-history-ids="selectedHistoryIds"
                @refreshList="load"
                @select="onSelectHistory"
                @updateFilter="updateFilterValue"
                @tagClick="(tag) => updateFilterValue('tag', `'${tag}'`)" />
        </BOverlay>

        <div class="d-flex mt-1 align-items-center">
            <div v-if="myView && selectedHistoryIds.length" class="d-flex flex-gapx-1 w-100 position-absolute">
                <BButton
                    v-if="!showDeleted"
                    id="history-list-footer-bulk-delete-button"
                    v-b-tooltip.hover
                    :title="bulkDeleteOrRestoreLoading ? 'Deleting histories' : 'Delete selected histories'"
                    :disabled="bulkDeleteOrRestoreLoading"
                    size="sm"
                    variant="primary"
                    @click="onBulkDelete">
                    <span v-if="!bulkDeleteOrRestoreLoading">
                        <FontAwesomeIcon :icon="faTrash" fixed-width />
                        Delete ({{ selectedHistoryIds.length }})
                    </span>
                    <LoadingSpan v-else message="Deleting" />
                </BButton>
                <BButton
                    v-else
                    id="history-list-footer-bulk-restore-button"
                    v-b-tooltip.hover
                    :title="bulkDeleteOrRestoreLoading ? 'Restoring histories' : 'Restore selected histories'"
                    :disabled="bulkDeleteOrRestoreLoading"
                    size="sm"
                    variant="primary"
                    @click="onBulkRestore">
                    <span v-if="!bulkDeleteOrRestoreLoading">
                        <FontAwesomeIcon :icon="faTrashRestore" fixed-width />
                        Restore ({{ selectedHistoryIds.length }})
                    </span>
                    <LoadingSpan v-else message="Restoring" />
                </BButton>

                <BButton
                    v-if="!showDeleted"
                    id="history-list-footer-bulk-add-tags-button"
                    v-b-tooltip.hover
                    :title="bulkTagsLoading ? 'Adding tags' : 'Add tags to selected histories'"
                    :disabled="bulkTagsLoading"
                    size="sm"
                    variant="primary"
                    @click="onToggleBulkTags">
                    <span v-if="!bulkTagsLoading">
                        <FontAwesomeIcon :icon="faTags" fixed-width />
                        Add tags ({{ selectedHistoryIds.length }})
                    </span>
                    <LoadingSpan v-else message="Adding tags" />
                </BButton>
            </div>

            <BPagination
                class="mx-0 my-auto w-100"
                :value="currentPage"
                :total-rows="totalHistories"
                :per-page="limit"
                align="right"
                size="sm"
                first-number
                last-number
                @change="onPageChange" />
        </div>

        <TagsSelectionDialog
            :show="showBulkAddTagsModal"
            :title="`Add tags to ${selectedHistoryIds.length} selected history${
                selectedHistoryIds.length > 1 ? 's' : ''
            }`"
            @cancel="onToggleBulkTags"
            @ok="onBulkTagsAdd" />
    </div>
</template>

<style scoped lang="scss">
.history-list-overlay {
    scroll-behavior: smooth;
    min-height: 150px;

    overflow-y: auto;
    overflow-x: hidden;
}
</style>
