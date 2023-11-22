<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faStar, faTrash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton, BNav, BNavItem, BOverlay } from "bootstrap-vue";
import { filter } from "underscore";
import { computed, type ComputedRef, onMounted, type Ref, ref, watch } from "vue";
import { useRouter } from "vue-router/composables";

import { loadWorkflows } from "@/components/Workflow/workflows.services";
import { useAnimationFrameResizeObserver } from "@/composables/sensors/animationFrameResizeObserver";
import { useAnimationFrameScroll } from "@/composables/sensors/animationFrameScroll";
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

library.add(faStar, faTrash);

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

const limit = ref(50);
const offset = ref(0);
const loading = ref(true);
const overlay = ref(false);
const isScrollable = ref(false);
const listHeader = ref<any>(null);
const workflows = ref<WorkflowsList>([]);
const advancedFiltering = ref<any>(null);
const scrollContainer: Ref<HTMLElement | null> = ref(null);

const { arrived } = useAnimationFrameScroll(scrollContainer);
useAnimationFrameResizeObserver(scrollContainer, ({ clientSize, scrollSize }) => {
    isScrollable.value = scrollSize.height >= clientSize.height + 1;
});

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

const filterText = ref("");
const showAdvanced = ref(false);
const showBookmarked = ref(false);
const WorkflowFilters = new Filtering(validFilters.value);
const published = computed(() => props.activeList === "published");
const scrolledTop = computed(() => !isScrollable.value || arrived.top);
const sharedWithMe = computed(() => props.activeList === "shared_with_me");
const showDeleted = computed(() => filterText.value.includes("is:deleted"));
const view = computed(() => (userStore.preferredListViewMode as ListView) || "grid");
const sortDesc = computed(() => (listHeader.value && listHeader.value.sortDesc) ?? true);
const sortBy = computed(() => (listHeader.value && listHeader.value.sortBy) || "update_time");
const noItems = computed(() => !loading.value && !overlay.value && workflows.value.length === 0 && !filterText.value);
const noResults = computed(() => !loading.value && !overlay.value && workflows.value.length === 0 && filterText.value);

function updateFilter(newVal: string) {
    advancedFiltering.value.updateFilter(newVal.trim());
}

function onTagClick(tag: string) {
    filterText.value = WorkflowFilters.setFilterValue(filterText.value, "tag", `'${tag}'`);
}

async function load(overlayLoading = false, silentLoading = false) {
    if (overlayLoading) {
        overlay.value = true;
    } else if (!silentLoading) {
        loading.value = true;
    }

    let search = filterText.value;

    if (published.value) {
        search += " is:published";
    }

    if (sharedWithMe.value) {
        search += " is:shared_with_me";
    }

    try {
        const tmp = await loadWorkflows({
            sortBy: sortBy.value,
            sortDesc: sortDesc.value,
            limit: limit.value,
            offset: offset.value,
            filterText: search?.trim(),
            showPublished: published.value,
            skipStepCounts: true,
        });

        let filteredWorkflows = showBookmarked.value
            ? filter(tmp, (workflow: any) => workflow.show_in_tool_panel)
            : tmp;

        if (props.activeList === "my") {
            filteredWorkflows = filter(filteredWorkflows, (w: any) => w.owner === userStore.currentUser?.username);
        }

        workflows.value = filteredWorkflows;
    } catch (e) {
        Toast.error(`Failed to load workflows: ${e}`);
    } finally {
        loading.value = false;
        overlay.value = false;
    }
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

watch([filterText, sortBy, sortDesc, showBookmarked], () => {
    load(true);
});

onMounted(() => {
    if (router.currentRoute.query.owner) {
        filterText.value = `${filterText.value} user:${router.currentRoute.query.owner}`.trim();
    }

    load();
});
</script>

<template>
    <div id="workflows-list" ref="scrollContainer" class="workflows-list">
        <div id="workflows-list-header" class="workflows-list-header mb-2" :class="{ 'scrolled-top': scrolledTop }">
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
                </template>
            </ListHeader>
        </div>

        <BAlert v-if="loading" variant="info" show>
            <LoadingSpan />
        </BAlert>

        <BAlert v-else-if="!loading && !overlay && noItems" id="workflow-list-empty" variant="info" show>
            No workflows found. You may create or import new workflows using the buttons above.
        </BAlert>

        <BAlert v-else-if="!loading && !overlay && noResults" id="no-workflow-found" variant="info" show>
            No workflows found matching: <span class="font-weight-bold">{{ filterText }}</span>
        </BAlert>

        <BOverlay
            v-else
            id="workflow-cards"
            :show="overlay"
            rounded="sm"
            class="cards-list mt-2"
            :class="view === 'grid' ? 'd-flex flex-wrap' : ''">
            <WorkflowCard
                v-for="workflow in workflows"
                :key="workflow.id"
                :class="view === 'grid' ? 'grid-view ' : ''"
                :workflow="workflow"
                :published-view="published"
                :grid-view="view === 'grid'"
                @refreshList="load"
                @tagClick="onTagClick" />
        </BOverlay>
    </div>
</template>

<style scoped lang="scss">
.workflows-list {
    container: workflow-list / inline-size;
    overflow: auto;

    .workflows-list-header {
        position: sticky;
        top: 0;
        z-index: 100;
        background-color: white;

        &:after {
            position: absolute;
            content: "";
            opacity: 0;
            z-index: 10;
            width: 100%;
            height: 20px;
            bottom: -25px;
            pointer-events: none;
            border-radius: 0.5rem;
            transition: opacity 0.4s;
            background-repeat: no-repeat;
        }

        &:after {
            right: 0;
            background-image: linear-gradient(to bottom, rgba(3, 0, 48, 0.1), rgba(3, 0, 48, 0.02), rgba(3, 0, 48, 0));
        }

        &:not(.scrolled-top) {
            &:after {
                opacity: 1;
            }
        }
    }

    .cards-list {
        min-height: 100px;
    }

    .grid-view {
        width: calc(100% / 3);
        display: inline-grid;
    }

    @container (max-width: 1200px) {
        .grid-view {
            width: calc(100% / 2);
            display: inline-grid;
        }
    }

    @container (max-width: 576px) {
        .grid-view {
            width: 100%;
            display: inline-grid;
        }
    }
}
</style>
