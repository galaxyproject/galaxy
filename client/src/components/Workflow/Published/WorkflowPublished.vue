<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faBuilding, faDownload, faEdit, faPlay, faSpinner, faUser } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import { until } from "@vueuse/core";
import { type AxiosError } from "axios";
import { BAlert, BButton, BCard } from "bootstrap-vue";
import { computed, nextTick, onMounted, ref, watch } from "vue";

import { getWorkflowInfo, type StoredWorkflowDetailed } from "@/api/workflows";
import { fromSimple } from "@/components/Workflow/Editor/modules/model";
import { getWorkflowFull } from "@/components/Workflow/workflows.services";
import { useDatatypesMapper } from "@/composables/datatypesMapper";
import { provideScopedWorkflowStores } from "@/composables/workflowStores";
import { useUserStore } from "@/stores/userStore";
import type { Steps } from "@/stores/workflowStepStore";
import { assertDefined } from "@/utils/assertions";
import { withPrefix } from "@/utils/redirect";

import ActivityBar from "@/components/ActivityBar/ActivityBar.vue";
import Heading from "@/components/Common/Heading.vue";
import WorkflowGraph from "@/components/Workflow/Editor/WorkflowGraph.vue";
import WorkflowInformation from "@/components/Workflow/Published/WorkflowInformation.vue";

library.add(faBuilding, faDownload, faEdit, faPlay, faSpinner, faUser);

interface Props {
    id: string;
    zoom?: number;
    embed?: boolean;
    initialX?: number;
    initialY?: number;
    quickView?: boolean;
    showAbout?: boolean;
    showHeading?: boolean;
    showMinimap?: boolean;
    showButtons?: boolean;
    showZoomControls?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
    zoom: 0.75,
    embed: false,
    initialX: -20,
    initialY: -20,
    quickView: false,
    showAbout: true,
    showHeading: true,
    showMinimap: true,
    showButtons: true,
    showZoomControls: true,
});

const userStore = useUserStore();

const { datatypesMapper } = useDatatypesMapper();

const { stateStore } = provideScopedWorkflowStores(props.id);

const loading = ref(true);
const errorMessage = ref("");
const workflowInfo = ref<StoredWorkflowDetailed>();
const workflow = ref<StoredWorkflowDetailed | null>(null);

const hasError = computed(() => !!errorMessage.value);

const downloadUrl = computed(() => withPrefix(`/api/workflows/${props.id}/download?format=json-download`));
const importUrl = computed(() => withPrefix(`/workflow/imp?id=${props.id}`));
const runUrl = computed(() => withPrefix(`/workflows/run?id=${props.id}`));

const initialPosition = computed(() => ({
    x: -props.initialX * props.zoom,
    y: -props.initialY * props.zoom,
}));

const viewUrl = computed(() => withPrefix(`/published/workflow?id=${props.id}`));

const sharedWorkflow = computed(() => {
    return !userStore.matchesCurrentUsername(workflowInfo.value?.owner);
});

const editButtonTitle = computed(() => {
    if (userStore.isAnonymous) {
        return "Log in to edit Workflow";
    } else {
        if (workflowInfo.value?.deleted) {
            return "You cannot edit a deleted workflow. Restore it first.";
        } else {
            return "Edit Workflow";
        }
    }
});

/** Workflow steps force typed as `Steps` from the `workflowStepStore` */
const workflowSteps = computed(() => (workflow.value?.steps as unknown as Steps) ?? []);

function logInTitle(title: string) {
    if (userStore.isAnonymous) {
        return `Log in to ${title}`;
    } else {
        return title;
    }
}

async function load() {
    errorMessage.value = "";

    try {
        const [workflowInfoData, fullWorkflow] = await Promise.all([
            getWorkflowInfo(props.id),
            getWorkflowFull(props.id),
        ]);

        assertDefined(workflowInfoData.name);

        workflowInfo.value = workflowInfoData;
        workflow.value = fullWorkflow;

        fromSimple(props.id, fullWorkflow);
    } catch (e) {
        const error = e as AxiosError<{ err_msg?: string }>;

        if (error.response?.data.err_msg) {
            errorMessage.value = error.response.data.err_msg ?? "Unknown Error";
        }
    } finally {
        loading.value = false;
    }
}

watch(
    () => props.zoom,
    () => (stateStore.scale = props.zoom),
    { immediate: true }
);

const workflowGraph = ref<InstanceType<typeof WorkflowGraph> | null>(null);

onMounted(async () => {
    await load();
    await until(workflow).toBeTruthy();
    await nextTick();

    // @ts-ignore: TS2339 webpack dev issue. hopefully we can remove this with vite
    workflowGraph.value?.fitWorkflow(0.25, 1.5, 20.0);
});
</script>

<template>
    <div id="columns" class="workflow-published">
        <ActivityBar v-if="!props.embed && !props.quickView" />

        <div id="center" class="container-root" :class="{ 'm-3': !props.quickView }">
            <div v-if="loading">
                <Heading h1 separator size="xl">
                    <FontAwesomeIcon :icon="faSpinner" spin />
                    Loading Workflow
                </Heading>
            </div>
            <div v-else-if="hasError">
                <Heading h1 separator size="xl"> Failed to load published Workflow </Heading>

                <BAlert show variant="danger">
                    {{ errorMessage }}
                </BAlert>
            </div>
            <div v-else-if="workflowInfo" class="published-workflow">
                <div v-if="props.showHeading || props.showButtons" class="workflow-header">
                    <Heading v-if="props.showHeading" h1 separator inline size="xl" class="flex-grow-1 mb-0">
                        <span v-if="props.showAbout"> Workflow Preview </span>
                        <span v-else> {{ workflowInfo.name }} </span>
                    </Heading>

                    <span v-if="props.showButtons">
                        <BButton
                            v-b-tooltip.hover.noninteractive
                            title="Download workflow in .ga format"
                            variant="outline-primary"
                            size="md"
                            :href="downloadUrl">
                            <FontAwesomeIcon :icon="faDownload" />
                            Download
                        </BButton>

                        <BButton
                            v-if="!props.embed && sharedWorkflow"
                            :href="importUrl"
                            :disabled="userStore.isAnonymous"
                            :title="logInTitle('Import Workflow')"
                            data-description="workflow import"
                            target="_blank"
                            variant="outline-primary"
                            size="md">
                            <FontAwesomeIcon :icon="faEdit" />
                            Import
                        </BButton>

                        <BButton
                            v-else-if="!props.embed && !sharedWorkflow"
                            v-b-tooltip.hover.noninteractive
                            :disabled="workflowInfo.deleted"
                            class="workflow-edit-button"
                            :title="editButtonTitle"
                            variant="outline-primary"
                            size="md"
                            :to="`/workflows/edit?id=${workflowInfo.id}`">
                            <FontAwesomeIcon :icon="faEdit" fixed-width />
                            Edit
                        </BButton>

                        <BButton
                            v-if="!props.embed"
                            :to="runUrl"
                            :disabled="userStore.isAnonymous"
                            :title="logInTitle('Run Workflow')"
                            variant="primary"
                            size="md">
                            <FontAwesomeIcon :icon="faPlay" />
                            Run
                        </BButton>

                        <BButton
                            v-if="props.embed"
                            :href="viewUrl"
                            target="blank"
                            variant="primary"
                            size="md"
                            class="view-button font-weight-bold">
                            <FontAwesomeIcon :icon="['gxd', 'galaxyLogo']" />
                            View In Galaxy
                        </BButton>
                    </span>
                </div>

                <BCard class="workflow-preview" :class="{ 'only-preview': !props.showAbout }">
                    <WorkflowGraph
                        v-if="workflow && datatypesMapper"
                        ref="workflowGraph"
                        :steps="workflowSteps"
                        :datatypes-mapper="datatypesMapper"
                        :initial-position="initialPosition"
                        :show-minimap="props.showMinimap"
                        :show-zoom-controls="props.showZoomControls"
                        readonly />
                </BCard>

                <WorkflowInformation
                    v-if="props.showAbout && workflowInfo"
                    class="workflow-information-container"
                    :workflow-info="workflowInfo"
                    :embedded="props.embed" />
            </div>
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

.workflow-published {
    display: flex;
    height: 100%;

    .container-root {
        container-type: inline-size;
        width: 100%;
        overflow: auto;
    }

    .published-workflow {
        display: grid;
        gap: 0.5rem 1rem;
        grid-template-rows: max-content;
        grid-template-columns: auto auto 30%;

        height: 100%;

        .workflow-header {
            grid-column: 1 / span 3;

            display: flex;
            justify-content: end;
        }

        .workflow-preview {
            grid-column: 1 / span 2;

            &.only-preview {
                grid-column: 1 / span 3;
            }
        }

        &:deep(.workflow-information-container) {
            height: 100%;
            max-width: 500px;
            overflow: auto;
        }
    }

    @container (max-width: 900px) {
        .published-workflow {
            height: unset;
            grid-template-columns: auto;

            .workflow-preview {
                grid-column: 1 / span 3;
                height: 450px;
            }

            &:deep(.workflow-information-container) {
                max-width: unset;
                height: unset;
            }

            .workflow-information-container {
                grid-column: 1 / span 3;
            }
        }
    }

    .view-button {
        --fa-secondary-color: #{$brand-toggle};
        --fa-secondary-opacity: 1;
    }
}
</style>
