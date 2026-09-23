<script setup lang="ts">
import { BPagination } from "bootstrap-vue";
import { computed, onMounted, ref, watch } from "vue";

import {
    type CuratedWorkflow,
    type CuratedWorkflowSortBy,
    type CuratedWorkflowSource,
    loadCuratedWorkflows,
} from "@/api/curatedWorkflows";
import { curatedHelpHtml, curatedWorkflowFilters } from "@/components/Workflow/List/curatedFilters";
import { useConfig } from "@/composables/config";
import { Toast } from "@/composables/toast";
import { useUserStore } from "@/stores/userStore";
import localize from "@/utils/localization";
import { errorMessageAsString } from "@/utils/simple-error";

import CuratedWorkflowCard from "./CuratedWorkflowCard.vue";
import WorkflowListTabs from "./WorkflowListTabs.vue";
import GAlert from "@/components/BaseComponents/GAlert.vue";
import GButton from "@/components/BaseComponents/GButton.vue";
import GLink from "@/components/BaseComponents/GLink.vue";
import GOverlay from "@/components/BaseComponents/GOverlay.vue";
import BreadcrumbHeading from "@/components/Common/BreadcrumbHeading.vue";
import FilterMenu from "@/components/Common/FilterMenu.vue";
import Heading from "@/components/Common/Heading.vue";
import ListHeader from "@/components/Common/ListHeader.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import WorkflowListActions from "@/components/Workflow/List/WorkflowListActions.vue";

const IWC_URL = "https://iwc.galaxyproject.org";

const breadcrumbItems = [{ title: "Workflows" }];

// Only the iwc source orders by runnability. In local mode the server's default
// is plain newest-first, which ListHeader's own initial "Update time" already
// describes truthfully, so there's no separate default to offer.
const RECOMMENDED_SORT = {
    label: localize("Recommended"),
    title: localize("Workflows that can run on this Galaxy first, then most recently updated"),
};

const userStore = useUserStore();
const { config, isConfigLoaded } = useConfig();

const limit = ref(24);
const offset = ref(0);
const loading = ref(true);
const overlay = ref(false);
const filterText = ref("");
const showAdvanced = ref(false);
const workflows = ref<CuratedWorkflow[]>([]);
const totalWorkflows = ref(0);
const source = ref<CuratedWorkflowSource | null>(null);
const message = ref<string | null>(null);
const loadError = ref<string | null>(null);
// Plain counter, not a ref: it guards which response may write state and must
// never itself be reactive.
let loadGeneration = 0;

const workflowFilters = curatedWorkflowFilters();

const rawFilters = computed(() => Object.fromEntries(workflowFilters.getFiltersForText(filterText.value, true, false)));
const validFilters = computed(() => workflowFilters.getValidFilters(rawFilters.value, true).validFilters);
const invalidFilters = computed(() => workflowFilters.getValidFilters(rawFilters.value, true).invalidFilters);
const isSurroundedByQuotes = computed(() => /^["'].*["']$/.test(filterText.value));
const hasInvalidFilters = computed(() => !isSurroundedByQuotes.value && Object.keys(invalidFilters.value).length > 0);

const currentPage = computed(() => Math.floor(offset.value / limit.value) + 1);
const currentListViewMode = computed(() => userStore.currentListViewPreferences.workflows || "grid");
const defaultSortOption = computed(() =>
    config.value?.curated_workflows_source === "iwc" ? RECOMMENDED_SORT : undefined,
);
// Null until the user picks a sort, and again once they pick "Recommended".
// Only an unsorted request gets the server's default order, which in iwc mode
// puts workflows that run here first. ListHeader keeps no persisted sort
// preference, so there is none to honour.
const explicitSort = ref<{ sortBy: CuratedWorkflowSortBy; sortDesc: boolean } | null>(null);

// Only consulted after the template's earlier branches have ruled out loading,
// errors and the preparing/unavailable states, so these say nothing about them.
const noItems = computed(() => totalWorkflows.value === 0 && !filterText.value);
const noResults = computed(() => totalWorkflows.value === 0 && Boolean(filterText.value));

async function load(overlayLoading = false) {
    // Bumped before the invalid-filter return, not after: typing a bad filter has
    // to retire whatever is already in flight, or that older response lands later
    // and repopulates the list underneath an invalid query.
    const generation = ++loadGeneration;

    if (hasInvalidFilters.value) {
        overlay.value = false;
        loading.value = false;
        return;
    }

    if (overlayLoading) {
        overlay.value = true;
    } else {
        loading.value = true;
    }

    try {
        const data = await loadCuratedWorkflows({
            search: validatedFilterText(),
            sortBy: explicitSort.value?.sortBy,
            sortDesc: explicitSort.value?.sortDesc,
            limit: limit.value,
            offset: offset.value,
        });

        if (generation !== loadGeneration) {
            return;
        }

        workflows.value = data.workflows ?? [];
        totalWorkflows.value = data.total_matches;
        source.value = data.source;
        message.value = data.message ?? null;
        loadError.value = null;

        // The catalog can shrink under a paged-in user (a refresh drops entries, an
        // owner unpublishes). Landing past the end returns a real total with no rows,
        // which no empty state covers, so step back to the last page that exists.
        if (totalWorkflows.value > 0 && workflows.value.length === 0 && offset.value >= totalWorkflows.value) {
            offset.value = Math.max(0, (Math.ceil(totalWorkflows.value / limit.value) - 1) * limit.value);
            await load(true);
            return;
        }
    } catch (e) {
        if (generation !== loadGeneration) {
            return;
        }
        // Kept on screen rather than only toasted: reaching this page with the
        // feature disabled is a 403, and a bare toast would leave a blank page.
        loadError.value = errorMessageAsString(e);
        Toast.error(`Failed to load curated workflows: ${loadError.value}`);
    } finally {
        if (generation === loadGeneration) {
            overlay.value = false;
            loading.value = false;
        }
    }
}

function validatedFilterText() {
    if (isSurroundedByQuotes.value) {
        return filterText.value.slice(1, -1);
    } else if (Object.keys(rawFilters.value).length === 0) {
        return filterText.value;
    }
    return workflowFilters.getFilterText(validFilters.value, true);
}

function updateFilterValue(filterKey: string, newValue: any) {
    filterText.value = workflowFilters.setFilterValue(filterText.value, filterKey, newValue);
}

async function onPageChange(page: number) {
    offset.value = (page - 1) * limit.value;
    await load(true);
}

function onSortChanged(sortBy: string, sortDesc: boolean) {
    explicitSort.value = { sortBy: sortBy as CuratedWorkflowSortBy, sortDesc };
}

function onSortDefault() {
    explicitSort.value = null;
}

watch([filterText, explicitSort], async () => {
    offset.value = 0;
    await load(true);
});

// No route watcher is needed: Analysis.vue keys <router-view> on the full path,
// so switching tabs remounts this component.
onMounted(() => load());
</script>

<template>
    <div id="curated-workflows-list" class="workflows-list">
        <div id="curated-workflows-list-header" class="workflows-list-header mb-2">
            <BreadcrumbHeading :items="breadcrumbItems">
                <WorkflowListActions />
            </BreadcrumbHeading>

            <WorkflowListTabs active="curated" />

            <div v-if="source === 'iwc'" id="curated-workflows-source-note" class="text-muted mb-2">
                <span v-localize>
                    Curated by the Intergalactic Workflow Commission. Import a workflow to add it to this Galaxy.
                </span>
                <GLink :href="IWC_URL" target="_blank">iwc.galaxyproject.org</GLink>
            </div>
            <div v-else-if="source === 'local'" id="curated-workflows-source-note" class="text-muted mb-2">
                <span v-localize>Workflows curated for this Galaxy.</span>
            </div>

            <FilterMenu
                id="curated-workflow-list-filter"
                name="curated workflows"
                :filter-class="workflowFilters"
                :filter-text.sync="filterText"
                :loading="loading || overlay"
                has-help
                view="compact"
                :placeholder="localize('Search curated workflows by query or use the advanced filtering options')"
                :show-advanced.sync="showAdvanced">
                <template v-slot:menu-help-text>
                    <!-- eslint-disable-next-line vue/no-v-html -->
                    <div v-html="curatedHelpHtml()"></div>
                </template>
            </FilterMenu>

            <!-- Waits for the config so ListHeader starts on the right default sort. -->
            <ListHeader
                v-if="isConfigLoaded"
                list-id="workflows"
                show-sort-options
                show-view-toggle
                :show-select-all="false"
                :default-sort-option="defaultSortOption"
                @sort-changed="onSortChanged"
                @sort-default="onSortDefault" />
        </div>

        <div v-if="loading" class="workflow-list-alert">
            <GAlert variant="info">
                <LoadingSpan message="Loading curated workflows" />
            </GAlert>
        </div>
        <div v-else-if="loadError" class="workflow-list-alert">
            <GAlert id="curated-workflows-error" variant="danger">
                <p>{{ loadError }}</p>
                <GButton id="curated-workflows-error-retry" size="small" color="blue" outline @click="load(true)">
                    <span v-localize>Try again</span>
                </GButton>
            </GAlert>
        </div>
        <div v-else-if="source === 'preparing'" class="workflow-list-alert">
            <GAlert id="curated-workflows-preparing" variant="info">
                <p>{{ message }}</p>
                <GButton id="curated-workflows-reload" size="small" color="blue" outline @click="load(true)">
                    <span v-localize>Reload</span>
                </GButton>
            </GAlert>
        </div>
        <div v-else-if="source === 'unavailable'" class="workflow-list-alert">
            <GAlert id="curated-workflows-unavailable" variant="warning">
                <p>{{ message }}</p>
                <p>
                    <span v-localize>You can browse the catalog at</span>
                    <GLink :href="IWC_URL" target="_blank">iwc.galaxyproject.org</GLink>
                    <span v-localize>or</span>
                    <GLink to="/workflows/import">import a workflow directly</GLink>
                    <span v-localize>.</span>
                </p>
                <GButton id="curated-workflows-retry" size="small" color="blue" outline @click="load(true)">
                    <span v-localize>Try again</span>
                </GButton>
            </GAlert>
        </div>
        <div v-else-if="!overlay && noItems" class="workflow-list-alert">
            <GAlert id="curated-workflows-empty" variant="info">
                <span v-if="source === 'local'" v-localize>
                    No curated workflows have been published on this Galaxy.
                </span>
                <span v-else v-localize>No curated workflows are available.</span>
            </GAlert>
        </div>
        <span v-else-if="!overlay && (noResults || hasInvalidFilters)" class="workflow-list-alert">
            <GAlert v-if="!hasInvalidFilters" id="no-curated-workflow-found" variant="info">
                No curated workflows found matching: <span class="font-weight-bold">{{ filterText }}</span>
                <GLink @click="filterText = ''">Reset the filter</GLink>
            </GAlert>

            <GAlert v-else id="no-curated-workflow-found-invalid" variant="danger">
                <Heading h4 inline size="sm" class="flex-grow-1 mb-2">Invalid filters in query:</Heading>
                <ul>
                    <li v-for="[invalidKey, value] in Object.entries(invalidFilters)" :key="invalidKey">
                        <b>{{ invalidKey }}</b
                        >: {{ value }}
                    </li>
                </ul>
                <GLink @click="filterText = validatedFilterText()"> Remove invalid filters from query </GLink>
            </GAlert>
        </span>
        <GOverlay v-else id="curated-workflow-cards" :show="overlay" class="cards-list">
            <div class="curated-workflow-card-list d-flex flex-wrap overflow-auto pt-1">
                <CuratedWorkflowCard
                    v-for="workflow in workflows"
                    :key="workflow.id"
                    :workflow="workflow"
                    :grid-view="currentListViewMode === 'grid'"
                    @tagClick="(tag) => updateFilterValue('tag', `'${tag}'`)" />
            </div>
        </GOverlay>

        <div v-if="totalWorkflows > limit" class="workflow-list-footer">
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
    </div>
</template>

<style scoped lang="scss">
// Mirrors WorkflowList.vue's layout, which lives in that component's own
// (unscoped) style block and is therefore not loaded on this route.
.workflows-list {
    overflow: auto;
    display: flex;
    flex-direction: column;

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

    .curated-workflow-card-list {
        container: cards-list / inline-size;
    }

    .workflow-list-footer {
        display: flex;
        align-items: center;
        margin-top: 0.5rem;

        .workflow-list-footer-pagination {
            margin: 0 auto;
            width: 100%;
        }
    }
}
</style>
