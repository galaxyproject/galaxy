<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faTrash } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton, BCol, BNav, BNavItem, BOverlay } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import { loadWorkflows } from "@/components/Workflow/workflows.services";
import { Toast } from "@/composables/toast";
import { useUserStore } from "@/stores/userStore";
import { contains, equals, expandNameTag, toBool } from "@/utils/filtering";

import AdvancedFiltering from "@/components/Common/AdvancedFiltering.vue";
import Heading from "@/components/Common/Heading.vue";
import ListHeader from "@/components/Common/ListHeader.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import WorkflowCard from "@/components/Workflow/WorkflowCard.vue";
import WorkflowListActions from "@/components/Workflow/WorkflowListActions.vue";

library.add(faTrash);

const filterOptions = [
    {
        filter: "name",
        description: "Shows workflows with the given sequence of characters in their names.",
    },
    {
        filter: "tag",
        description:
            "Shows workflows with the given workflow tag. You may also click on a tag to filter on that tag directly.",
    },
    {
        filter: "is:published",
        description: "Shows published workflows.",
    },
    {
        filter: "is:importable",
        description: "Shows importable workflows (this also means they have URL generated).",
    },
    {
        filter: "is:shared_with_me",
        description: "Shows workflows shared by another user directly with you.",
    },
    {
        filter: "is:deleted",
        description: "Shows deleted workflows.",
    },
];

type ListView = "grid" | "list";
type WorkflowsList = Record<string, never>[];

interface Props {
    activeList?: "my" | "shared_with_me" | "published";
}

const props = withDefaults(defineProps<Props>(), {
    activeList: "my",
});

const userStore = useUserStore();

const validFilters = {
    name: contains("name"),
    tag: contains("tags", "tag", expandNameTag),
    deleted: contains("deleted", "true", toBool),
    published: equals("published", "true", toBool),
    importable: contains("importable", "true", toBool),
    shared_with_me: contains("shared_with_me", "true", toBool),
};

const limit = ref(50);
const offset = ref(0);
const loading = ref(true);
const overlay = ref(false);
const showDeleted = ref(false);
const listHeader = ref<any>(null);
const workflows = ref<WorkflowsList>([]);
const advancedFiltering = ref<any>(null);

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

const filters = computed(() => advancedFiltering.value.filters);
const published = computed(() => props.activeList === "published");
const sharedWithMe = computed(() => props.activeList === "shared_with_me");
const view = computed(() => (userStore.preferredListViewMode as ListView) || "grid");
const sortDesc = computed(() => (listHeader.value && listHeader.value.sortDesc) || true);
const sortBy = computed(() => (listHeader.value && listHeader.value.sortBy) || "update_time");
const filterText = computed(() => advancedFiltering.value && advancedFiltering.value.filterText);
const noItems = computed(() => !loading.value && workflows.value.length === 0 && !filterText.value);
const noResults = computed(() => !loading.value && workflows.value.length === 0 && filterText.value);

function updateFilter(newVal: string) {
    advancedFiltering.value.updateFilter(newVal.trim());
}

function onTagClick(tag: { text: string }) {
    updateFilter(filters.value.setFilterValue(filterText.value, "tag", tag.text));
}

async function load(overlayLoading = false) {
    if (overlayLoading) {
        overlay.value = true;
    } else {
        loading.value = true;
    }

    let search = filterText.value;

    if (published.value) {
        search += " is:published";
    }

    if (sharedWithMe.value) {
        search += " is:shared_with_me";
    }

    if (showDeleted.value) {
        search += " is:deleted";
    }

    try {
        workflows.value = await loadWorkflows({
            sortBy: sortBy.value,
            sortDesc: sortDesc.value,
            limit: limit.value,
            offset: offset.value,
            filterText: search?.trim(),
            showPublished: published.value,
            skipStepCounts: true,
        });
    } catch (e) {
        Toast.error(`Failed to load workflows: ${e}`);
    } finally {
        loading.value = false;
        overlay.value = false;
    }
}

load();

watch([filterText, sortBy, sortDesc, showDeleted], () => {
    load(true);
});
</script>

<template>
    <div id="workflows-list" class="workflows-list">
        <div id="workflows-list-header" class="mb-2">
            <div class="d-flex">
                <Heading h1 separator inline size="xl" class="flex-grow-1 mb-2">Workflows</Heading>

                <WorkflowListActions />
            </div>

            <BNav tabs fill>
                <BNavItem :active="activeList === 'my'" to="/workflows/list">My workflows</BNavItem>
                <BNavItem :active="sharedWithMe" to="/workflows/list_shared_with_me">
                    Workflows shared with me
                </BNavItem>
                <BNavItem :active="published" to="/workflows/list_published"> Public workflows </BNavItem>
            </BNav>

            <AdvancedFiltering
                ref="advancedFiltering"
                advanced-mode
                help-title="Workflows"
                :filter-options="filterOptions"
                :valid-filters="validFilters"
                :search-place-holder="searchPlaceHolder" />

            <ListHeader ref="listHeader" show-view-toggle>
                <template v-slot:extra-filter>
                    <BCol v-if="activeList === 'my'">
                        Filter:
                        <BButton
                            id="show-deleted"
                            v-b-tooltip.hover
                            size="sm"
                            :title="showDeleted ? 'Show deleted workflows' : 'Hide deleted workflows'"
                            :pressed="showDeleted"
                            variant="outline-primary"
                            @click="showDeleted = !showDeleted">
                            <FontAwesomeIcon :icon="faTrash" />
                            Show deleted
                        </BButton>
                    </BCol>
                </template>
            </ListHeader>
        </div>

        <BAlert v-if="loading" variant="info" show>
            <LoadingSpan />
        </BAlert>

        <BAlert v-else-if="!loading && noItems" variant="info" show>
            No workflows found. You may create or import new workflows using the buttons above.
        </BAlert>

        <BAlert v-else-if="!loading && noResults" variant="info" show>
            No workflows found matching: <span class="font-weight-bold">{{ filterText }}</span>
        </BAlert>

        <BOverlay
            v-else
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
    container-type: inline-size;
    overflow: auto;

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
