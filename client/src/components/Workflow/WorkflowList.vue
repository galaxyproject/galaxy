<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faGlobe, faStar, faTrash, faUpload } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert, BButton, BNav, BNavItem, BOverlay, BPagination } from "bootstrap-vue";
import { filter } from "underscore";
import { computed, type ComputedRef, onMounted, ref, watch } from "vue";
import { useRouter } from "vue-router/composables";

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

const helpHtml = `<div>
<p>This input can be used to filter the workflows displayed.</p>

<p>
    Text entered here will be searched against workflow names and workflow
    tags. Additionally, advanced filtering tags can be used to refine the
    search more precisely. Filtering tags are of the form
    <code>&lt;tag_name&gt;:&lt;tag_value&gt;</code> or
    <code>&lt;tag_name&gt;:'&lt;tag_value&gt;'</code>. For instance to
    search just for RNAseq in the workflow name,
    <code>name:rnsseq</code> can be used. Notice by default the search is
    not case-sensitive. If the quoted version of tag is used, the search is
    case sensitive and only full matches will be returned. So
    <code>name:'RNAseq'</code> would show only workflows named exactly
    <code>RNAseq</code>.
</p>

<p>The available filtering tags are:</p>
<dl>
    <dt><code>name</code></dt>
    <dd>
        Shows workflows with the given sequence of characters in their names.
    </dd>
    <dt><code>tag</code></dt>
    <dd>
        Shows workflows with the given workflow tag. You may also click
        on a tag to filter on that tag directly.
    </dd>
</dl>
</div>`;

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

const limit = ref(24);
const offset = ref(0);
const loading = ref(true);
const overlay = ref(false);
const filterText = ref("");
const totalWorkflows = ref(0);
const showAdvanced = ref(false);
const showBookmarked = ref(false);
const listHeader = ref<any>(null);
const advancedFiltering = ref<any>(null);
const workflowsLoaded = ref<WorkflowsList>([]);

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
const currentPage = computed(() => Math.floor(offset.value / limit.value) + 1);
const view = computed(() => (userStore.preferredListViewMode as ListView) || "grid");
const sortDesc = computed(() => (listHeader.value && listHeader.value.sortDesc) ?? true);
const sortBy = computed(() => (listHeader.value && listHeader.value.sortBy) || "update_time");
const noItems = computed(() => !loading.value && workflowsLoaded.value.length === 0 && !filterText.value);
const noResults = computed(() => !loading.value && workflowsLoaded.value.length === 0 && filterText.value);

function updateFilter(newVal: string) {
    advancedFiltering.value.updateFilter(newVal.trim());
}

function onTagClick(tag: string) {
    if (filterText.value.includes(tag)) {
        filterText.value = filterText.value.replace(`tag:'${tag}'`, "").trim();
    } else {
        filterText.value = WorkflowFilters.setFilterValue(filterText.value, "tag", `'${tag}'`);
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

async function load(overlayLoading = false, silent = false) {
    if (!silent) {
        if (overlayLoading) {
            overlay.value = true;
        } else {
            loading.value = true;
        }
    }

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

        workflowsLoaded.value = filteredWorkflows;

        if (showBookmarked.value) {
            totalWorkflows.value = filteredWorkflows.length;
        } else {
            totalWorkflows.value = parseInt(headers.get("Total_matches") || "0", 10) || 0;
        }
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

watch([filterText, sortBy, sortDesc, showBookmarked], async () => {
    offset.value = 0;
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
                :loading="loading || overlay"
                has-help
                :placeholder="searchPlaceHolder"
                :show-advanced.sync="showAdvanced"
                @updateFilter="updateFilter">
                <template v-slot:menu-help-text>
                    <div v-html="helpHtml"></div>
                </template>
            </FilterMenu>

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
                            <FontAwesomeIcon :icon="faTrash" fixed-width />
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
                            <FontAwesomeIcon :icon="faStar" fixed-width />
                            Show bookmarked
                        </BButton>
                    </div>
                </template>
            </ListHeader>
        </div>

        <BAlert v-if="loading" variant="info" show>
            <LoadingSpan message="Loading workflows..." />
        </BAlert>

        <BAlert v-if="!loading && !overlay && noItems" id="workflow-list-empty" variant="info" show>
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
                v-for="w in workflowsLoaded"
                :key="w.id"
                :workflow="w"
                :published-view="published"
                :grid-view="view === 'grid'"
                :class="view === 'grid' ? 'grid-view' : 'list-view'"
                @refreshList="load"
                @tagClick="onTagClick" />

            <BPagination
                v-if="!loading && totalWorkflows > limit"
                class="mt-2 w-100"
                :value="currentPage"
                :total-rows="totalWorkflows"
                :per-page="limit"
                align="center"
                first-number
                last-number
                @change="onPageChange" />
        </BOverlay>
    </div>
</template>

<style lang="scss">
@import "scss/mixins.scss";
@import "breakpoints.scss";

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

    .cards-list {
        container: card-list / inline-size;
        scroll-behavior: smooth;
        min-height: 150px;

        overflow-y: auto;
        overflow-x: hidden;

        .list-view {
            width: 100%;
        }

        .grid-view {
            width: calc(100% / 3);
        }

        @container card-list (max-width: #{$breakpoint-xl}) {
            .grid-view {
                width: calc(100% / 2);
            }
        }

        @container card-list (max-width: #{$breakpoint-sm}) {
            .grid-view {
                width: 100%;
            }
        }
    }
}
</style>
