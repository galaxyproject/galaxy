<script setup lang="ts">
import { faPlus } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { useMemoize, watchImmediate } from "@vueuse/core";
import { BButton } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import { loadWorkflows, type WorkflowSummary } from "@/api/workflows";
import { useAnimationFrameScroll } from "@/composables/sensors/animationFrameScroll";
import { useToast } from "@/composables/toast";

import ActivityPanel from "./ActivityPanel.vue";
import FavoritesButton from "./Buttons/FavoritesButton.vue";
import DelayedInput from "@/components/Common/DelayedInput.vue";
import ScrollToTopButton from "@/components/ToolsList/ScrollToTopButton.vue";
import WorkflowCardList from "@/components/Workflow/List/WorkflowCardList.vue";

const props = defineProps<{
    currentWorkflowId: string;
}>();

const emit = defineEmits<{
    (e: "insertWorkflow", id: string, name: string): void;
    (e: "insertWorkflowSteps", id: string, stepCount: number): void;
    (e: "createWorkflow"): void;
}>();

const scrollable = ref<HTMLDivElement | null>(null);
const { arrived, scrollTop } = useAnimationFrameScroll(scrollable);

const loading = ref(false);
const totalWorkflowsCount = ref(Infinity);

const allLoaded = computed(() => totalWorkflowsCount.value <= workflows.value.length);

const filterText = ref("");

const workflows = ref<WorkflowSummary[]>([]);

const showFavorites = computed({
    get() {
        return filterText.value.includes("is:bookmarked");
    },
    set(value) {
        if (value) {
            if (!filterText.value.includes("is:bookmarked")) {
                filterText.value = `is:bookmarked ${filterText.value}`.trim();
            }
        } else {
            filterText.value = filterText.value.replace("is:bookmarked", "").trim();
        }
    },
});

const loadWorkflowsOptions = {
    sortBy: "update_time",
    sortDesc: true,
    limit: 20,
    showPublished: false,
    skipStepCounts: false,
} as const;

const { error } = useToast();
const getWorkflows = useMemoize(async (filterText: string, offset: number) => {
    const { data, totalMatches } = await loadWorkflows({
        ...loadWorkflowsOptions,
        offset,
        filterText,
    });

    return { data, totalMatches };
});

let fetchKey = "";
let lastFetchKey = "";

async function load() {
    const isCurrentFetch = () => fetchKey.trim().toLowerCase() === lastFetchKey.trim().toLowerCase();

    if (isCurrentFetch() && (loading.value || allLoaded.value)) {
        return;
    }

    lastFetchKey = fetchKey;

    loading.value = true;

    try {
        const { data, totalMatches } = await getWorkflows(filterText.value, workflows.value.length);

        if (isCurrentFetch()) {
            totalWorkflowsCount.value = totalMatches;

            const workflowIds = new Set(workflows.value.map((w) => w.id));
            const newWorkflows = data.filter((w) => !workflowIds.has(w.id));

            workflows.value.push(...newWorkflows);
        }
    } catch (e) {
        if (isCurrentFetch()) {
            error(`Failed to load workflows: ${e}`);
        }
    } finally {
        if (isCurrentFetch()) {
            loading.value = false;
        }
    }
}

function resetWorkflows() {
    workflows.value = [];
    totalWorkflowsCount.value = Infinity;
    loading.value = false;
    fetchKey = "";
}

function refresh() {
    resetWorkflows();
    getWorkflows.clear();
    load();
}

watchImmediate(
    () => filterText.value,
    (newFilterText) => {
        showFavorites.value = newFilterText.includes("is:bookmarked");
        resetWorkflows();
        fetchKey = filterText.value;
        load();
    }
);

watch(
    () => arrived.bottom,
    () => {
        if (arrived.bottom) {
            load();
        }
    }
);

function scrollToTop() {
    scrollable.value?.scrollTo({ top: 0, behavior: "smooth" });
}

function createNew(event: Event) {
    event.preventDefault();
    emit("createWorkflow");
}
</script>

<template>
    <ActivityPanel title="Workflows">
        <template v-slot:header-buttons>
            <BButton
                v-b-tooltip.hover.top.noninteractive
                size="sm"
                variant="link"
                class="create-button"
                title="Create new workflow"
                href="/workflows/edit"
                @click="createNew">
                <FontAwesomeIcon :icon="faPlus" />
            </BButton>
            <FavoritesButton v-model="showFavorites" tooltip="Show bookmarked" />
        </template>

        <DelayedInput
            v-model="filterText"
            placeholder="search workflows"
            :delay="800"
            :loading="loading"></DelayedInput>

        <div ref="scrollable" class="workflow-scroll-list mt-2">
            <WorkflowCardList
                :hide-runs="true"
                :workflows="workflows"
                :filterable="false"
                :current-workflow-id="props.currentWorkflowId"
                editor-view
                @insertWorkflow="(...args) => emit('insertWorkflow', ...args)"
                @insertWorkflowSteps="(...args) => emit('insertWorkflowSteps', ...args)"
                @refreshList="refresh" />

            <div v-if="allLoaded || filterText !== ''" class="list-end">
                <span v-if="workflows.length == 1"> - 1 workflow loaded - </span>
                <span v-else-if="workflows.length > 1"> - All {{ workflows.length }} workflows loaded - </span>
                <span v-else> - No workflows found - </span>
            </div>
            <div v-else-if="loading" class="list-end">- loading -</div>
        </div>

        <ScrollToTopButton :offset="scrollTop" @click="scrollToTop" />
    </ActivityPanel>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

.workflow-scroll-list {
    overflow-y: auto;
    display: flex;
    flex-direction: column;
}

.list-end {
    align-self: center;
    color: $text-light;
    margin: 0.5rem;
}

.create-button:hover {
    background-color: #c8cfd6;
    border-color: #c1c9d0;
}
</style>
