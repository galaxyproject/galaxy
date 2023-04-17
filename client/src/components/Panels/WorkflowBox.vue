<script setup lang="ts">
import { getGalaxyInstance } from "@/app";
import { getAppRoot } from "@/onload";
import { useRouter } from "vue-router/composables";
import { ref, computed, onMounted, type ComputedRef } from "vue";
import { useWorkflowStore, type Workflow } from "@/stores/workflowStore";
import WorkflowSearch from "@/components/Workflow/WorkflowSearch.vue";
import FavoritesButton from "@/components/Panels/Buttons/FavoritesButton.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";

const workflowStore = useWorkflowStore();
const router = useRouter();

const query = ref("");
const queryPending = ref(false);
const showAdvanced = ref(false);

const panelFilter: ComputedRef<any> = computed(() => {
    return { name: query.value };
});

// on Mount, load all Workflows
onMounted(async () => {
    queryPending.value = true;
    await workflowStore.fetchWorkflows(panelFilter.value);
    queryPending.value = false;
});

// computed
const workflows = computed(() => {
    let results: Workflow[] = [];
    if (query.value === "#favorites") {
        const Galaxy = getGalaxyInstance();
        results = Galaxy.config.stored_workflow_menu_entries;
    } else if (!queryTooShort.value) {
        results = workflowStore.getWorkflows(panelFilter.value);
    }
    return [
        ...results.map((wf) => {
            return {
                id: wf.id,
                name: wf.name,
                href: `${getAppRoot()}workflows/run?id=${wf.id}`,
            };
        }),
    ];
});
const queryTooShort: ComputedRef<boolean> = computed(() => query.value !== "" && query.value.length < 3);

// functions
async function onQuery(q: string) {
    query.value = !q ? "" : q;
    queryPending.value = true;
    if (!queryTooShort.value && q !== "#favorites") {
        await workflowStore.fetchWorkflows(panelFilter.value);
    }
    queryPending.value = false;
}
function onOpen(route: string) {
    router.push(route);
}
</script>

<template>
    <div class="unified-panel" aria-labelledby="workflowbox-heading">
        <div unselectable="on">
            <div class="unified-panel-header-inner">
                <nav class="d-flex justify-content-between mx-3 my-2">
                    <h2 v-if="!showAdvanced" id="workflowbox-heading" v-localize class="m-1 h-sm">Workflows</h2>
                    <h2 v-else id="workflowbox-heading" v-localize class="m-1 h-sm">Advanced Workflow Search</h2>

                    <div class="panel-header-buttons">
                        <b-button-group>
                            <favorites-button v-if="!showAdvanced" :query="query" @onFavorites="onQuery" />
                        </b-button-group>
                    </div>
                </nav>
            </div>
        </div>
        <div class="unified-panel-controls">
            <WorkflowSearch enable-advanced :show-advanced.sync="showAdvanced" :query="query" @onQuery="onQuery" />
            <section v-if="!showAdvanced">
                <div v-if="queryPending" class="pb-2">
                    <b-badge class="alert-info w-100"><LoadingSpan message="Loading workflows" /></b-badge>
                </div>
                <div v-else-if="queryTooShort" class="pb-2">
                    <b-badge class="alert-danger w-100">Search string too short!</b-badge>
                </div>
                <div v-else-if="workflows.length == 0" class="pb-2">
                    <b-badge class="alert-danger w-100">No results found!</b-badge>
                </div>
            </section>
        </div>
        <div v-if="!showAdvanced" class="unified-panel-body">
            <div class="toolMenuContainer">
                <div id="internal-workflows" class="toolSectionBody">
                    <div class="toolSectionBg" />
                    <div v-for="wf in workflows" :key="wf.id" class="toolTitle">
                        <a class="title-link" href="javascript:void(0)" @click="onOpen(wf.href)">{{ wf.name }}</a>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>
