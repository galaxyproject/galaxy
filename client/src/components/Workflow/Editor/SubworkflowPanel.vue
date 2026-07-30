<script setup lang="ts">
/**
 * Opens a subworkflow over the workflow being edited, as a graph you can click through and a
 * form for whichever step you pick, so a subworkflow can be changed without leaving the
 * workflow that uses it.
 *
 * The subworkflow gets its own set of scoped stores, keyed by its own id, which is what lets
 * the ordinary graph and inspector components be reused for it unchanged.
 */
import { faTimes } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { BAlert } from "bootstrap-vue";
import { computed, ref, watch } from "vue";

import type { DatatypesMapperModel } from "@/components/Datatypes/model";
import { getWorkflowFull } from "@/components/Workflow/workflows.services";
import { provideScopedWorkflowStores } from "@/composables/workflowStores";
import type { PostJobActions } from "@/stores/workflowStepStore";
import { errorMessageAsString } from "@/utils/simple-error";

import { useStepActions } from "./Actions/stepActions";
import { fromSimple } from "./modules/model";

import GButton from "@/components/BaseComponents/GButton.vue";
import LoadingSpan from "@/components/LoadingSpan.vue";
import NodeInspector from "@/components/Workflow/Editor/NodeInspector.vue";
import WorkflowGraph from "@/components/Workflow/Editor/WorkflowGraph.vue";

const props = defineProps<{
    /** Encoded id of the subworkflow revision to show, the step's content_id. */
    contentId: string;
    /** Names of the workflows above this one, outermost first, for the breadcrumb. */
    trailNames: string[];
    datatypes: string[];
    datatypesMapper: DatatypesMapperModel;
}>();

const emit = defineEmits<{
    (e: "close"): void;
    /** Open a subworkflow found inside this one, one level deeper. */
    (e: "openNested", contentId: string, name: string, stepOrderIndex: number): void;
    /** The user applied their edits, the caller saves them and refreshes the step. */
    (e: "apply", contentId: string, workflow: unknown): void;
}>();

// Scoped to the subworkflow, so the graph and inspector below resolve to its steps and not
// to the ones of the workflow this panel is drawn over.
const scopedId = computed(() => `subworkflow-panel-${props.contentId}`);
const { stepStore, stateStore, connectionStore, undoRedoStore, commentStore } = provideScopedWorkflowStores(scopedId);
const stepActions = useStepActions(stepStore, undoRedoStore, stateStore, connectionStore);

const loading = ref(true);
const errorMessage = ref<string | null>(null);
const workflowName = ref("");
const loadedWorkflow = ref<Record<string, any> | null>(null);
const dirty = ref(false);

const activeStep = computed(() =>
    stateStore.activeNodeId !== null ? stepStore.getStep(stateStore.activeNodeId) : null,
);
const breadcrumb = computed(() => [...props.trailNames, workflowName.value].filter(Boolean));

async function load() {
    loading.value = true;
    errorMessage.value = null;
    dirty.value = false;
    try {
        const data = await getWorkflowFull(props.contentId);
        stepStore.$reset();
        stateStore.$reset();
        connectionStore.$reset();
        commentStore.$reset();
        await fromSimple(scopedId.value, data);
        loadedWorkflow.value = data;
        workflowName.value = data.name;
    } catch (error) {
        errorMessage.value = errorMessageAsString(error);
    } finally {
        loading.value = false;
    }
}

watch(() => props.contentId, load, { immediate: true });

function onStepUpdated(_id: string, step: any) {
    stepStore.updateStep(step);
    dirty.value = true;
}

function onSetData(id: string, data: any) {
    stepActions.updateStep(Number(id), data);
    dirty.value = true;
}

function onLabel(id: string, label: string) {
    const step = stepStore.getStep(Number(id));
    if (step) {
        stepActions.setLabel(step, label);
        dirty.value = true;
    }
}

function onAnnotation(id: string, annotation: string) {
    stepActions.updateStep(Number(id), { annotation });
    dirty.value = true;
}

function onPostJobActions(id: string, postJobActions: unknown) {
    stepActions.updateStep(Number(id), { post_job_actions: postJobActions as PostJobActions });
    dirty.value = true;
}

/** A subworkflow step inside this subworkflow, opened one level deeper in the same panel. */
function onOpenNested(contentId: string, stepId: number) {
    const step = stepStore.getStep(stepId);
    emit("openNested", contentId, step?.label || step?.name || "subworkflow", stepId);
}

function onApply() {
    if (!loadedWorkflow.value) {
        return;
    }
    emit("apply", props.contentId, {
        ...loadedWorkflow.value,
        name: workflowName.value,
        steps: stepStore.steps,
        comments: commentStore.comments,
    });
}
</script>

<template>
    <div class="subworkflow-panel">
        <header class="subworkflow-panel-header">
            <nav class="subworkflow-panel-breadcrumb" aria-label="subworkflow path">
                <span v-for="(crumb, index) in breadcrumb" :key="index">{{ crumb }}</span>
            </nav>
            <GButton icon-only transparent title="Close without applying" @click="emit('close')">
                <FontAwesomeIcon :icon="faTimes" />
            </GButton>
        </header>

        <BAlert v-if="errorMessage" variant="danger" show class="m-2">{{ errorMessage }}</BAlert>

        <div v-else class="subworkflow-panel-body">
            <LoadingSpan v-if="loading" message="Loading the subworkflow" />
            <WorkflowGraph
                v-else
                :steps="stepStore.steps"
                :datatypes-mapper="datatypesMapper"
                :show-minimap="false"
                :initial-position="{ x: 40, y: 40 }"
                @onChange="dirty = true">
                <NodeInspector
                    v-if="activeStep"
                    :step="activeStep"
                    :datatypes="datatypes"
                    @stepUpdated="onStepUpdated"
                    @dataChanged="onSetData"
                    @labelChanged="onLabel"
                    @annotationChanged="onAnnotation"
                    @postJobActionsChanged="onPostJobActions"
                    @editSubworkflow="onOpenNested"
                    @close="stateStore.activeNodeId = null" />
            </WorkflowGraph>
        </div>

        <footer class="subworkflow-panel-footer">
            <span class="text-muted">
                {{
                    dirty
                        ? "Applying saves the subworkflow and updates the step that uses it."
                        : "Click a step to edit it."
                }}
            </span>
            <GButton @click="emit('close')">Cancel</GButton>
            <GButton color="blue" :disabled="!dirty || loading" @click="onApply">Apply changes</GButton>
        </footer>
    </div>
</template>

<style scoped lang="scss">
@import "@/style/scss/theme/blue.scss";

.subworkflow-panel {
    position: absolute;
    inset: 2rem;
    z-index: 2000;
    display: flex;
    flex-direction: column;
    background: $white;
    border: 1px solid $brand-primary;
    border-radius: 0.25rem;
    box-shadow: 0 0.5rem 2rem rgba(0, 0, 0, 0.3);
    overflow: hidden;
}

.subworkflow-panel-header {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.25rem 0.5rem 0.25rem 1rem;
    background: $brand-info;
    color: $white;
}

.subworkflow-panel-breadcrumb {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    overflow: hidden;
    font-weight: 700;
    margin-right: auto;

    span + span::before {
        content: "\203a";
        margin-right: 0.4rem;
        font-weight: 400;
    }
}

.subworkflow-panel-body {
    position: relative;
    flex-grow: 1;
    overflow: hidden;
}

.subworkflow-panel-footer {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 1rem;
    border-top: 1px solid $border-color;

    .text-muted {
        margin-right: auto;
    }
}
</style>
