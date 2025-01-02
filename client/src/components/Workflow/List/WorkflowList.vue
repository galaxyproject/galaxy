<script setup lang="ts">
import { faStar, faTags, faTrash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton, BNav, BNavItem, BOverlay, BPagination } from "bootstrap-vue";
import { faTrashRestore } from "font-awesome-6";
import { filter } from "underscore";
import { computed, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router/composables";

import { GalaxyApi } from "@/api";
import { getWorkflowFilters, helpHtml } from "@/components/Workflow/List/workflowFilters";
import { deleteWorkflow, undeleteWorkflow, updateWorkflow } from "@/components/Workflow/workflows.services";
import { useConfirmDialog } from "@/composables/confirmDialog";
import { Toast } from "@/composables/toast";
import { useUserStore } from "@/stores/userStore";
import { rethrowSimple } from "@/utils/simple-error";

import WorkflowCardList from "./WorkflowCardList.vue";
import FilterMenu from "@/components/Common/FilterMenu.vue";
import Heading from "@/components/Common/Heading.vue";
import ListHeader from "@/components/Common/ListHeader.vue";
import LoginRequired from "@/components/Common/LoginRequired.vue";
import TagsSelectionDialog from "@/components/Common/TagsSelectionDialog.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import WorkflowListActions from "@/components/Workflow/List/WorkflowListActions.vue";

type ListView = "grid" | "list";
type WorkflowsList = Record<string, never>[];

// Temporary interface to match the `Workflow` interface from `WorkflowCard`
interface SelectedWorkflow {
    id: string;
    name: string;
    published: boolean;
}

interface Props {
    activeList?: "my" | "shared_with_me" | "published";
}

const props = withDefaults(defineProps<Props>(), {
    activeList: "my",
});

const router = useRouter();
const userStore = useUserStore();
const { confirm } = useConfirmDialog();

const limit = ref(24);
const offset = ref(0);
const loading = ref(true);
const overlay = ref(false);
const filterText = ref("");
const totalWorkflows = ref(0);
const showAdvanced = ref(false);
const listHeader = ref<any>(null);
const showBulkAddTagsModal = ref(false);
const bulkTagsLoading = ref(false);
const bulkDeleteOrRestoreLoading = ref(false);
const workflowsLoaded = ref<WorkflowsList>([]);
const selectedWorkflowIds = ref<SelectedWorkflow[]>([]);

const searchPlaceHolder = computed(() => {
    let placeHolder = "Search my workflows";

    if (published.value) {
        placeHolder = "Search published workflows";
    } else if (sharedWithMe.value) {
        placeHolder = "Search workflows shared with me";
    }

    placeHolder += " by query or use the advanced filtering options";

    return placeHolder;
});

const published = computed(() => props.activeList === "published");
const sharedWithMe = computed(() => props.activeList === "shared_with_me");
const showDeleted = computed(() => filterText.value.includes("is:deleted"));
const showBookmarked = computed(() => filterText.value.includes("is:bookmarked"));
const currentPage = computed(() => Math.floor(offset.value / limit.value) + 1);
const view = computed(() => (userStore.preferredListViewMode as ListView) || "grid");
const sortDesc = computed(() => (listHeader.value && listHeader.value.sortDesc) ?? true);
const sortBy = computed(() => (listHeader.value && listHeader.value.sortBy) || "update_time");
const noItems = computed(() => !loading.value && workflowsLoaded.value.length === 0 && !filterText.value);
const noResults = computed(() => !loading.value && workflowsLoaded.value.length === 0 && Boolean(filterText.value));
const deleteButtonTitle = computed(() => (showDeleted.value ? "Hide deleted workflows" : "Show deleted workflows"));
const bookmarkButtonTitle = computed(() =>
    showBookmarked.value ? "Hide bookmarked workflows" : "Show bookmarked workflows"
);

const workflowFilters = computed(() => getWorkflowFilters(props.activeList));
const rawFilters = computed(() =>
    Object.fromEntries(workflowFilters.value.getFiltersForText(filterText.value, true, false))
);
const validFilters = computed(() => workflowFilters.value.getValidFilters(rawFilters.value, true).validFilters);
const invalidFilters = computed(() => workflowFilters.value.getValidFilters(rawFilters.value, true).invalidFilters);
const isSurroundedByQuotes = computed(() => /^["'].*["']$/.test(filterText.value));
const hasInvalidFilters = computed(() => !isSurroundedByQuotes.value && Object.keys(invalidFilters.value).length > 0);
const indeterminateSelected = computed(() => selectedWorkflowIds.value.length > 0 && !allSelected.value);
const allSelected = computed(
    () => selectedWorkflowIds.value.length !== 0 && selectedWorkflowIds.value.length === workflowsLoaded.value.length
);

function updateFilterValue(filterKey: string, newValue: any) {
    const currentFilterText = filterText.value;
    filterText.value = workflowFilters.value.setFilterValue(currentFilterText, filterKey, newValue);
}

function onToggleBookmarked() {
    updateFilterValue("bookmarked", true);
}

function onToggleDeleted() {
    updateFilterValue("deleted", true);
}

async function load(overlayLoading = false, silent = false) {
    if (!silent) {
        if (overlayLoading) {
            overlay.value = true;
        } else {
            loading.value = true;
        }
    }

    let search;

    if (!hasInvalidFilters.value) {
        search = validatedFilterText();

        // append default backend query filters for provided `props.activeList`
        if (published.value && !workflowFilters.value.getFilterValue(search, "published")) {
            search += " is:published";
        }
        if (sharedWithMe.value && !workflowFilters.value.getFilterValue(search, "shared_with_me")) {
            search += " is:shared_with_me";
        }
    } else {
        // there are invalid filters, so we don't want to search
        overlay.value = false;
        loading.value = false;
        return;
    }

    try {
        const { response, data, error } = await GalaxyApi().GET("/api/workflows", {
            params: {
                query: {
                    sort_by: sortBy.value,
                    sort_desc: sortDesc.value,
                    limit: limit.value,
                    offset: offset.value,
                    search: search?.trim(),
                    show_published: published.value,
                    skip_step_counts: true,
                },
            },
        });

        if (error) {
            rethrowSimple(error);
        }

        let filteredWorkflows = data;

        if (props.activeList === "my") {
            filteredWorkflows = filter(filteredWorkflows, (w: any) => userStore.matchesCurrentUsername(w.owner));
        }

        workflowsLoaded.value = filteredWorkflows;

        totalWorkflows.value = parseInt(response.headers.get("Total_matches") || "0", 10) || 0;
    } catch (e) {
        Toast.error(`Failed to load workflows: ${e}`);
    } finally {
        overlay.value = false;
        loading.value = false;
    }
}

async function onPageChange(page: number) {
    offset.value = (page - 1) * limit.value;
    await load(true);
}

function validatedFilterText() {
    if (isSurroundedByQuotes.value) {
        // the `filterText` is surrounded by quotes, remove them
        return filterText.value.slice(1, -1);
    } else if (Object.keys(rawFilters.value).length === 0) {
        // there are no filters derived from the `filterText`
        return filterText.value;
    }
    // there are valid filters derived from the `filterText`
    return workflowFilters.value.getFilterText(validFilters.value, true);
}

function onSelectWorkflow(w: SelectedWorkflow) {
    const index = selectedWorkflowIds.value.findIndex((selected) => selected.id === w.id);

    if (index === -1) {
        selectedWorkflowIds.value.push(w);
    } else {
        selectedWorkflowIds.value.splice(index, 1);
    }
}

function onSelectAllWorkflows() {
    if (selectedWorkflowIds.value.length === workflowsLoaded.value.length) {
        selectedWorkflowIds.value = [];
    } else {
        selectedWorkflowIds.value = workflowsLoaded.value.map((w: any) => {
            return {
                id: w.id,
                name: w.name,
                published: w.published,
            };
        });
    }
}

async function onBulkDelete() {
    const totalSelected = selectedWorkflowIds.value.length;
    const hasPublished = selectedWorkflowIds.value.some((w) => w.published);

    const confirmed = await confirm(
        `${hasPublished ? "Some of the selected workflows are published and will be removed from public view. " : ""}
            Are you sure you want to delete ${totalSelected} workflows?`,
        {
            title: "Delete workflows",
            okTitle: "Delete workflows",
            okVariant: "danger",
        }
    );

    if (confirmed) {
        const tmpSelected = [...selectedWorkflowIds.value];

        try {
            overlay.value = true;
            bulkDeleteOrRestoreLoading.value = true;

            for (const w of selectedWorkflowIds.value) {
                await deleteWorkflow(w.id);

                tmpSelected.splice(
                    tmpSelected.findIndex((s) => s.id === w.id),
                    1
                );
            }

            Toast.success(`Deleted ${totalSelected} workflows.`);

            selectedWorkflowIds.value = [];
        } catch (e) {
            Toast.error(`Failed to delete some workflows.`);
        } finally {
            bulkDeleteOrRestoreLoading.value = false;

            selectedWorkflowIds.value = tmpSelected;

            await load(true);
        }
    }
}

async function onBulkRestore() {
    const totalSelected = selectedWorkflowIds.value.length;

    const confirmed = await confirm(`Are you sure you want to restore ${totalSelected} workflows?`, {
        okTitle: "Restore workflows",
        okVariant: "primary",
    });

    if (confirmed) {
        const tmpSelected = [...selectedWorkflowIds.value];

        try {
            overlay.value = true;
            bulkDeleteOrRestoreLoading.value = true;

            for (const w of selectedWorkflowIds.value) {
                await undeleteWorkflow(w.id);

                tmpSelected.splice(
                    tmpSelected.findIndex((s) => s.id === w.id),
                    1
                );
            }

            Toast.success(`Restored ${totalSelected} workflows.`);

            selectedWorkflowIds.value = [];
        } catch (e) {
            Toast.error(`Failed to restore some workflows.`);
        } finally {
            bulkDeleteOrRestoreLoading.value = false;

            selectedWorkflowIds.value = tmpSelected;

            await load(true);
        }
    }
}

async function onToggleBulkTags() {
    showBulkAddTagsModal.value = !showBulkAddTagsModal.value;
}

async function onBulkTagsAdd(tags: string[]) {
    const tmpSelected = [...selectedWorkflowIds.value];
    const totalSelected = selectedWorkflowIds.value.length;

    try {
        overlay.value = true;
        bulkTagsLoading.value = true;

        for (const w of selectedWorkflowIds.value) {
            const prevTags = workflowsLoaded.value.find((workflow) => workflow.id === w.id)?.tags || [];

            await updateWorkflow(w.id, { tags: [...new Set([...prevTags, ...tags])] });

            tmpSelected.splice(
                tmpSelected.findIndex((s) => s.id === w.id),
                1
            );
        }

        Toast.success(`Added tag(s) to ${totalSelected} workflows.`);
    } catch (e) {
        Toast.error(`Failed to add tag(s) to some workflows. ${e}`);
    } finally {
        bulkTagsLoading.value = false;

        selectedWorkflowIds.value = tmpSelected;

        await load(true);
    }
}

watch([filterText, sortBy, sortDesc], async () => {
    offset.value = 0;

    selectedWorkflowIds.value = [];

    await load(true);
});

onMounted(() => {
    if (router.currentRoute.query.owner) {
        updateFilterValue("user", `'${router.currentRoute.query.owner}'`);
    }
    load();
});
</script>

<template>
    <div id="workflows-list" class="workflows-list">
        <div id="workflows-list-header" class="workflows-list-header mb-2">
            <div class="d-flex flex-gapx-1">
                <Heading h1 separator inline size="xl" class="flex-grow-1 mb-2">Workflows</Heading>

                <WorkflowListActions />
            </div>

            <BNav pills justified class="mb-2">
                <BNavItem id="my" :active="activeList === 'my'" :disabled="userStore.isAnonymous" to="/workflows/list">
                    My workflows
                    <LoginRequired v-if="userStore.isAnonymous" target="my" title="Manage your workflows" />
                </BNavItem>

                <BNavItem
                    id="shared-with-me"
                    :active="sharedWithMe"
                    :disabled="userStore.isAnonymous"
                    to="/workflows/list_shared_with_me">
                    Workflows shared with me
                    <LoginRequired v-if="userStore.isAnonymous" target="shared-with-me" title="Manage your workflows" />
                </BNavItem>

                <BNavItem id="published" :active="published" to="/workflows/list_published">
                    Public workflows
                </BNavItem>
            </BNav>

            <FilterMenu
                id="workflow-list-filter"
                name="workflows"
                class="mb-2"
                :filter-class="workflowFilters"
                :filter-text.sync="filterText"
                :loading="loading || overlay"
                has-help
                view="compact"
                :placeholder="searchPlaceHolder"
                :show-advanced.sync="showAdvanced">
                <template v-slot:menu-help-text>
                    <div v-html="helpHtml(activeList)"></div>
                </template>
            </FilterMenu>

            <ListHeader
                ref="listHeader"
                show-view-toggle
                :show-select-all="!published && !sharedWithMe"
                :select-all-disabled="loading || overlay || noItems || noResults"
                :all-selected="allSelected"
                :indeterminate-selected="indeterminateSelected"
                @select-all="onSelectAllWorkflows">
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

                        <BButton
                            id="show-bookmarked"
                            v-b-tooltip.hover
                            size="sm"
                            :title="bookmarkButtonTitle"
                            :pressed="showBookmarked"
                            variant="outline-primary"
                            @click="onToggleBookmarked">
                            <FontAwesomeIcon :icon="faStar" fixed-width />
                            Show bookmarked
                        </BButton>
                    </div>
                </template>
            </ListHeader>
        </div>

        <div v-if="loading" class="workflow-list-alert">
            <BAlert variant="info" show>
                <LoadingSpan message="Loading workflows" />
            </BAlert>
        </div>
        <div v-else-if="!loading && !overlay && noItems" class="workflow-list-alert">
            <BAlert id="workflow-list-empty" variant="info" show>
                No workflows found. You may create or import new workflows using the buttons above.
            </BAlert>
        </div>
        <span v-else-if="!loading && !overlay && (noResults || hasInvalidFilters)" class="workflow-list-alert">
            <BAlert v-if="!hasInvalidFilters" id="no-workflow-found" variant="info" show>
                No workflows found matching: <span class="font-weight-bold">{{ filterText }}</span>
            </BAlert>

            <BAlert v-else id="no-workflow-found-invalid" variant="danger" show>
                <Heading h4 inline size="sm" class="flex-grow-1 mb-2">Invalid filters in query:</Heading>
                <ul>
                    <li v-for="[invalidKey, value] in Object.entries(invalidFilters)" :key="invalidKey">
                        <b>{{ invalidKey }}</b
                        >: {{ value }}
                    </li>
                </ul>
                <a href="javascript:void(0)" class="ui-link" @click="filterText = validatedFilterText()">
                    Remove invalid filters from query
                </a>
                or
                <a
                    v-b-tooltip.noninteractive.hover
                    title="Note that this might produce inaccurate results"
                    href="javascript:void(0)"
                    class="ui-link"
                    @click="filterText = `'${filterText}'`">
                    Match the exact query provided
                </a>
            </BAlert>
        </span>
        <BOverlay v-else id="workflow-cards" :show="overlay" rounded="sm" class="cards-list">
            <WorkflowCardList
                :workflows="workflowsLoaded"
                :published-view="published"
                :grid-view="view === 'grid'"
                :selected-workflow-ids="selectedWorkflowIds"
                @select="onSelectWorkflow"
                @refreshList="load"
                @tagClick="(tag) => updateFilterValue('tag', `'${tag}'`)"
                @updateFilter="updateFilterValue" />
        </BOverlay>

        <div class="workflow-list-footer">
            <div
                v-if="!published && !sharedWithMe && selectedWorkflowIds.length"
                class="workflow-list-footer-bulk-actions">
                <BButton
                    v-if="!showDeleted"
                    id="workflow-list-footer-bulk-delete-button"
                    v-b-tooltip.hover
                    :title="bulkDeleteOrRestoreLoading ? 'Deleting workflows' : 'Delete selected workflows'"
                    :disabled="bulkDeleteOrRestoreLoading"
                    size="sm"
                    variant="primary"
                    @click="onBulkDelete">
                    <span v-if="!bulkDeleteOrRestoreLoading">
                        <FontAwesomeIcon :icon="faTrash" fixed-width />
                        Delete ({{ selectedWorkflowIds.length }})
                    </span>
                    <LoadingSpan v-else message="Deleting" />
                </BButton>
                <BButton
                    v-else
                    id="workflow-list-footer-bulk-restore-button"
                    v-b-tooltip.hover
                    :title="bulkDeleteOrRestoreLoading ? 'Restoring workflows' : 'Restore selected workflows'"
                    :disabled="bulkDeleteOrRestoreLoading"
                    size="sm"
                    variant="primary"
                    @click="onBulkRestore">
                    <span v-if="!bulkDeleteOrRestoreLoading">
                        <FontAwesomeIcon :icon="faTrashRestore" fixed-width />
                        Restore ({{ selectedWorkflowIds.length }})
                    </span>
                    <LoadingSpan v-else message="Restoring" />
                </BButton>

                <BButton
                    v-if="!showDeleted"
                    id="workflow-list-footer-bulk-add-tags-button"
                    v-b-tooltip.hover
                    :title="bulkTagsLoading ? 'Adding tags' : 'Add tags to selected workflows'"
                    :disabled="bulkTagsLoading"
                    size="sm"
                    variant="primary"
                    @click="onToggleBulkTags">
                    <span v-if="!bulkTagsLoading">
                        <FontAwesomeIcon :icon="faTags" fixed-width />
                        Add tags ({{ selectedWorkflowIds.length }})
                    </span>
                    <LoadingSpan v-else message="Adding tags" />
                </BButton>
            </div>

            <BPagination
                class="workflow-list-footer-pagination"
                :value="currentPage"
                :total-rows="totalWorkflows"
                :per-page="limit"
                align="right"
                size="sm"
                first-number
                last-number
                @change="onPageChange" />
        </div>

        <TagsSelectionDialog
            v-if="showBulkAddTagsModal"
            :title="`Add tags to ${selectedWorkflowIds.length} selected workflow${
                selectedWorkflowIds.length > 1 ? 's' : ''
            }`"
            @cancel="onToggleBulkTags"
            @ok="onBulkTagsAdd" />
    </div>
</template>

<style lang="scss">
.workflows-list {
    overflow: auto;
    display: flex;
    flex-direction: column;

    .workflow-total {
        display: grid;
        text-align: center;
        margin-top: 1rem;
    }

    .workflows-list-header {
        top: 0;
        z-index: 100;
    }

    .workflow-list-alert {
        height: 100%;
    }

    .cards-list {
        height: 100%;
        scroll-behavior: smooth;
        min-height: 150px;
        display: flex;
        flex-direction: column;

        overflow-y: auto;
        overflow-x: hidden;
    }

    .workflow-list-footer {
        display: flex;
        align-items: center;
        margin-top: 0.5rem;

        .workflow-list-footer-bulk-actions {
            display: flex;
            gap: 0.5rem;
            width: 100%;
            position: absolute;
        }

        .workflow-list-footer-pagination {
            margin: 0 auto;
            width: 100%;
        }
    }
}
</style>
