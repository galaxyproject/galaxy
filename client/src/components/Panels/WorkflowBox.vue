<script setup lang="ts">
import { getGalaxyInstance } from "@/app";
import { getAppRoot } from "@/onload";
import { withPrefix } from "@/utils/redirect";
import { useRouter } from "vue-router/composables";
import { ref, computed, onMounted, type ComputedRef } from "vue";
import { useWorkflowStore, type Workflow } from "@/stores/workflowStore";
import WorkflowSearch from "@/components/Workflow/WorkflowSearch.vue";
import FavoritesButton from "@/components/Panels/Buttons/FavoritesButton.vue";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { faUpload } from "@fortawesome/free-solid-svg-icons";
import { library } from "@fortawesome/fontawesome-svg-core";

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

//@ts-ignore bad library types
library.add(faUpload);

// computed
const isUser: ComputedRef<boolean> = computed(() => {
    const Galaxy = getGalaxyInstance();
    return !!(Galaxy.user && Galaxy.user.id);
});
const workflows = computed(() => {
    if (isUser.value) {
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
    }
    return [];
});
const hasWorkflows: ComputedRef<boolean> = computed(() => workflows.value.length !== 0);
const hasQuery: ComputedRef<boolean> = computed(() => query.value !== "");
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

                    <div v-if="isUser" class="panel-header-buttons">
                        <b-button-group>
                            <favorites-button v-if="!showAdvanced" :query="query" @onFavorites="onQuery" />
                            <b-button
                                v-b-tooltip.bottom.hover
                                data-description="create new workflow"
                                size="sm"
                                variant="link"
                                title="Create new workflow"
                                @click="$router.push('/workflows/create')">
                                <Icon fixed-width icon="plus" />
                            </b-button>
                        </b-button-group>
                    </div>
                </nav>
            </div>
        </div>
        <div v-if="!isUser">
            <b-badge class="alert-info w-100">
                Please <a :href="withPrefix('/login')">log in or register</a> to use this feature.
            </b-badge>
        </div>
        <div v-else>
            <div class="unified-panel-controls">
                <WorkflowSearch
                    enable-advanced
                    :loading="queryPending"
                    :show-advanced.sync="showAdvanced"
                    :query="query"
                    @onQuery="onQuery" />
                <div v-if="!showAdvanced">
                    <b-button
                        id="workflow-import"
                        class="upload-button"
                        size="sm"
                        @click="$router.push('/workflows/import')">
                        <FontAwesomeIcon icon="upload" />
                        Import Workflow
                    </b-button>
                    <div v-if="!queryPending" class="pb-2">
                        <b-badge class="alert-danger w-100">
                            <span v-if="queryTooShort">Search string too short!</span>
                            <span v-else-if="!hasQuery && !hasWorkflows">No workflows found!</span>
                            <span v-else-if="hasQuery && !hasWorkflows">No results found!</span>
                        </b-badge>
                    </div>
                </div>
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
    </div>
</template>
