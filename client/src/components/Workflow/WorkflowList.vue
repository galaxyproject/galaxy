<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faGlobe, faStar, faTrash, faUpload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton, BNav, BNavItem } from "bootstrap-vue";
import { filter } from "underscore";
import { computed, type ComputedRef, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router/composables";
//@ts-ignore missing typedefs
import VirtualList from "vue-virtual-scroll-list";

import { loadWorkflows } from "@/components/Workflow/workflows.services";
import { Toast } from "@/composables/toast";
import { useUserStore } from "@/stores/userStore";
import Filtering, { contains, equals, expandNameTag, toBool, type ValidFilter } from "@/utils/filtering";

import FilterMenu from "@/components/Common/FilterMenu.vue";
import Heading from "@/components/Common/Heading.vue";
import ListHeader from "@/components/Common/ListHeader.vue";
import LoginRequired from "@/components/Common/LoginRequired.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import WorkflowCard from "@/components/Workflow/WorkflowCard.vue";
import WorkflowListActions from "@/components/Workflow/WorkflowListActions.vue";

library.add(faGlobe, faStar, faTrash, faUpload);

type ListView = "grid" | "list";
type WorkflowsList = Record<string, never>[];

interface Props {
    activeList?: "my" | "shared_with_me" | "published";
}

const props = withDefaults(defineProps<Props>(), {
    activeList: "my",
});

const router = useRouter();
const userStore = useUserStore();

const limit = ref(70);
const offset = ref(0);
const loading = ref(true);
const filterText = ref("");
const showAdvanced = ref(false);
const showBookmarked = ref(false);
const listHeader = ref<any>(null);
const advancedFiltering = ref<any>(null);
const workflowsLoaded = ref<WorkflowsList>([]);
const totalWorkflows = ref<number | null>(null);
const showHighlight = ref<"published" | "imported" | "">("");

const validFilters: ComputedRef<Record<string, ValidFilter<string | boolean | undefined>>> = computed(() => {
    return {
        name: { placeholder: "name", type: String, handler: contains("name"), menuItem: true },
        tag: {
            placeholder: "tag",
            type: "MultiTags",
            handler: contains("tags", "tag", expandNameTag),
            menuItem: true,
        },
        deleted: {
            placeholder: "Filter on deleted workflows",
            type: Boolean,
            handler: equals("deleted", "deleted", toBool),
            menuItem: false,
        },
    };
});

const WorkflowFilters = new Filtering(validFilters.value);

const searchPlaceHolder = computed(() => {
    let placeHolder = "Search my workflows";

    if (published.value) {
        placeHolder = "Search published workflows";
    } else if (sharedWithMe.value) {
        placeHolder = "Search workflows shared with me";
    }

    placeHolder += " by name or use the advanced filtering options";

    return placeHolder;
});

const published = computed(() => props.activeList === "published");
const sharedWithMe = computed(() => props.activeList === "shared_with_me");
const showDeleted = computed(() => filterText.value.includes("is:deleted"));
const view = computed(() => (userStore.preferredListViewMode as ListView) || "grid");
const sortDesc = computed(() => (listHeader.value && listHeader.value.sortDesc) ?? true);
const sortBy = computed(() => (listHeader.value && listHeader.value.sortBy) || "update_time");
const noItems = computed(() => !loading.value && workflowsLoaded.value.length === 0 && !filterText.value);
const noResults = computed(() => !loading.value && workflowsLoaded.value.length === 0 && filterText.value);

function updateFilter(newVal: string) {
    advancedFiltering.value.updateFilter(newVal.trim());
}

function onTagClick(tag: string) {
    filterText.value = WorkflowFilters.setFilterValue(filterText.value, "tag", `'${tag}'`);
}

function onToggleDeleted() {
    if (!showDeleted.value) {
        filterText.value = `${filterText.value} is:deleted`.trim();
    } else {
        filterText.value = filterText.value.replace("is:deleted", "").trim();
    }
}

function onToggleBookmarked() {
    showBookmarked.value = !showBookmarked.value;
}

function onToggleShowHighlight(h: "published" | "imported") {
    if (showHighlight.value === h) {
        showHighlight.value = "";
    } else {
        showHighlight.value = h;
    }
}

async function load(reset = false) {
    totalWorkflows.value = 0;

    loading.value = true;

    let search = filterText.value;

    if (published.value) {
        search += " is:published";
    }

    if (sharedWithMe.value) {
        search += " is:shared_with_me";
    }

    try {
        const { data, headers } = await loadWorkflows({
            sortBy: sortBy.value,
            sortDesc: sortDesc.value,
            limit: limit.value,
            offset: offset.value,
            filterText: search?.trim(),
            showPublished: published.value,
            skipStepCounts: true,
        });

        let filteredWorkflows = showBookmarked.value
            ? filter(data, (workflow: any) => workflow.show_in_tool_panel)
            : data;

        if (props.activeList === "my") {
            filteredWorkflows = filter(filteredWorkflows, (w: any) => w.owner === userStore.currentUser?.username);
        }

        if (reset) {
            workflowsLoaded.value = filteredWorkflows;
        } else {
            workflowsLoaded.value.push(...filteredWorkflows);
        }

        if (showBookmarked.value) {
            totalWorkflows.value = filteredWorkflows.length;
        } else {
            totalWorkflows.value = parseInt(headers.get("Total_matches") || "0", 10) || null;
        }
    } catch (e) {
        Toast.error(`Failed to load workflows: ${e}`);
    } finally {
        loading.value = false;
    }
}

async function onToBottom() {
    if (workflowsLoaded.value.length < totalWorkflows.value!) {
        offset.value += limit.value;
        await load();
    }
}

watch([filterText, sortBy, sortDesc, showBookmarked], async () => {
    console.log("filterText changed", filterText.value, sortBy.value, sortDesc.value, showBookmarked.value);
    offset.value = 0;
    workflowsLoaded.value = [];
    await load(true);
});

onMounted(() => {
    if (router.currentRoute.query.owner) {
        filterText.value = `${filterText.value} user:${router.currentRoute.query.owner}`.trim();
    }
    load();
});
</script>

<template>
    <div id="workflows-list" class="workflows-list">
        <div id="workflows-list-header" class="workflows-list-header mb-2">
            <div class="d-flex">
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
                :filter-class="WorkflowFilters"
                :filter-text.sync="filterText"
                :loading="loading"
                has-help
                :placeholder="searchPlaceHolder"
                :show-advanced.sync="showAdvanced"
                @updateFilter="updateFilter" />

            <ListHeader ref="listHeader" show-view-toggle>
                <template v-slot:extra-filter>
                    <div v-if="activeList === 'my'">
                        Filter:
                        <BButton
                            id="show-deleted"
                            v-b-tooltip.hover
                            size="sm"
                            :title="!showDeleted ? 'Show deleted workflows' : 'Hide deleted workflows'"
                            :pressed="showDeleted"
                            variant="outline-primary"
                            @click="onToggleDeleted">
                            <FontAwesomeIcon :icon="faTrash" />
                            Show deleted
                        </BButton>

                        <BButton
                            id="show-bookmarked"
                            v-b-tooltip.hover
                            size="sm"
                            :title="!showBookmarked ? 'Show bookmarked workflows' : 'Hide bookmarked workflows'"
                            :pressed="showBookmarked"
                            variant="outline-primary"
                            @click="onToggleBookmarked">
                            <FontAwesomeIcon :icon="faStar" />
                            Show bookmarked
                        </BButton>
                    </div>

                    <div v-if="activeList !== 'published'">
                        Highlights:
                        <BButton
                            id="highlight-published-workflows"
                            v-b-tooltip.hover
                            size="sm"
                            :title="
                                showHighlight === 'published'
                                    ? 'Highlight published workflows'
                                    : 'Hide published workflows highlight'
                            "
                            :pressed="showHighlight === 'published'"
                            variant="outline-primary"
                            @click="onToggleShowHighlight('published')">
                            <FontAwesomeIcon :icon="faGlobe" />
                            Published
                        </BButton>

                        <BButton
                            id="highlight-imported-workflows"
                            v-b-tooltip.hover
                            size="sm"
                            :title="
                                showHighlight === 'imported'
                                    ? 'Highlight imported workflows'
                                    : 'Hide imported workflows highlight'
                            "
                            :pressed="showHighlight === 'imported'"
                            variant="outline-primary"
                            @click="onToggleShowHighlight('imported')">
                            <FontAwesomeIcon :icon="faUpload" />
                            Imported
                        </BButton>
                    </div>
                </template>
            </ListHeader>
        </div>

        <BAlert v-if="!loading && noItems" id="workflow-list-empty" variant="info" show>
            No workflows found. You may create or import new workflows using the buttons above.
        </BAlert>

        <BAlert v-else-if="!loading && noResults" id="no-workflow-found" variant="info" show>
            No workflows found matching: <span class="font-weight-bold">{{ filterText }}</span>
        </BAlert>

        <div class="listing-layout position-relative">
            <VirtualList
                id="workflow-cards"
                role="list"
                class="listing"
                :data-key="'id'"
                :wrap-class="'cards-list'"
                :data-component="{}"
                :item-class="view === 'grid' ? 'grid-view' : 'list-view'"
                :data-sources="workflowsLoaded"
                @tobottom="onToBottom">
                <template v-slot:item="{ item }">
                    <WorkflowCard
                        :key="item.id"
                        :workflow="item"
                        :show-highlight="showHighlight"
                        :published-view="published"
                        :grid-view="view === 'grid'"
                        @refreshList="load"
                        @tagClick="onTagClick" />
                </template>

                <template v-slot:footer>
                    <BAlert v-if="loading" variant="info" show class="mt-2">
                        <LoadingSpan message="Loading workflows..." />
                    </BAlert>

                    <span v-if="totalWorkflows" class="workflow-total">
                        --- {{ workflowsLoaded.length }} workflows loaded out of {{ totalWorkflows }} ---
                    </span>
                </template>
            </VirtualList>
        </div>
    </div>
</template>

<style lang="scss">
@import "scss/mixins.scss";
@import "breakpoints.scss";

.workflows-list {
    display: flex;
    flex-direction: column;

    .listing-layout {
        height: 100%;

        .listing {
            @include absfill();
            scroll-behavior: smooth;
            overflow-y: auto;
            overflow-x: hidden;
        }
    }

    .workflow-total {
        display: grid;
        text-align: center;
        margin-top: 1rem;
    }

    .workflows-list-header {
        top: 0;
        z-index: 100;
        background-color: white;
    }

    .cards-list {
        container: card-list / inline-size;
        scroll-behavior: smooth;

        display: flex;
        flex-wrap: wrap;

        .list-view {
            width: 100%;
        }

        .grid-view {
            width: calc(100% / 3);
            display: inline-grid;
        }

        @container card-list (max-width: #{$breakpoint-xl}) {
            .grid-view {
                width: calc(100% / 2);
                display: inline-grid;
            }
        }

        @container card-list (max-width: #{$breakpoint-sm}) {
            .grid-view {
                width: 100%;
                display: inline-grid;
            }
        }
    }
}
</style>
