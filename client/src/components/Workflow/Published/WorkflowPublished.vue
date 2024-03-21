<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faBuilding, faDownload, faEdit, faPlay, faSpinner, faUser } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import axios, { type AxiosError } from "axios";
import { computed, ref, watch } from "vue";

import { fromSimple } from "@/components/Workflow/Editor/modules/model";
import { useDatatypesMapper } from "@/composables/datatypesMapper";
import { usePanels } from "@/composables/usePanels";
import { provideScopedWorkflowStores } from "@/composables/workflowStores";
import { useUserStore } from "@/stores/userStore";
import type { Workflow } from "@/stores/workflowStore";
import { assertDefined } from "@/utils/assertions";
import { withPrefix } from "@/utils/redirect";

import WorkflowInformation from "./WorkflowInformation.vue";
import ActivityBar from "@/components/ActivityBar/ActivityBar.vue";
import Heading from "@/components/Common/Heading.vue";
import FlexPanel from "@/components/Panels/FlexPanel.vue";
import ToolPanel from "@/components/Panels/ToolPanel.vue";
import WorkflowGraph from "@/components/Workflow/Editor/WorkflowGraph.vue";

library.add(faSpinner, faUser, faBuilding, faPlay, faEdit, faDownload);

const props = defineProps({
    id: {
        type: String,
        required: true,
    },
    zoom: {
        type: Number,
        default: 0.75,
    },
    embed: {
        type: Boolean,
        default: false,
    },
    showButtons: {
        type: Boolean,
        default: true,
    },
    showAbout: {
        type: Boolean,
        default: true,
    },
    showHeading: {
        type: Boolean,
        default: true,
    },
    showMinimap: {
        type: Boolean,
        default: true,
    },
    showZoomControls: {
        type: Boolean,
        default: true,
    },
    initialX: {
        type: Number,
        default: -20,
    },
    initialY: {
        type: Number,
        default: -20,
    },
});

const workflowInfo = ref<
    | {
          name: string;
          [key: string]: unknown;
          license?: string;
          tags?: string[];
          update_time: string;
      }
    | undefined
>();

const workflow = ref<Workflow | null>(null);

const loading = ref(true);
const errored = ref(false);
const errorMessage = ref("");

const { datatypesMapper } = useDatatypesMapper();

const { stateStore } = provideScopedWorkflowStores(props.id);

watch(
    () => props.zoom,
    () => (stateStore.scale = props.zoom),
    { immediate: true }
);

watch(
    () => props.id,
    async (id) => {
        workflowInfo.value = undefined;
        loading.value = true;
        errored.value = false;
        errorMessage.value = "";

        try {
            const [{ data: workflowInfoData }, { data: fullWorkflow }] = await Promise.all([
                axios.get(withPrefix(`/api/workflows/${id}`)),
                axios.get(withPrefix(`/workflow/load_workflow?_=true&id=${id}`)),
            ]);

            assertDefined(workflowInfoData.name);

            workflowInfo.value = workflowInfoData;
            workflow.value = fullWorkflow;

            fromSimple(props.id, fullWorkflow);
        } catch (e) {
            const error = e as AxiosError<{ err_msg?: string }>;

            if (error.response?.data.err_msg) {
                errorMessage.value = error.response.data.err_msg;
            }

            errored.value = true;
        } finally {
            loading.value = false;
        }
    },
    {
        immediate: true,
    }
);

const { showActivityBar, showToolbox } = usePanels();

const downloadUrl = computed(() => withPrefix(`/api/workflows/${props.id}/download?format=json-download`));
const importUrl = computed(() => withPrefix(`/workflow/imp?id=${props.id}`));
const runUrl = computed(() => withPrefix(`/workflows/run?id=${props.id}`));

const userStore = useUserStore();

function logInTitle(title: string) {
    if (userStore.isAnonymous) {
        return `Log in to ${title}`;
    } else {
        return title;
    }
}

const initialPosition = computed(() => ({
    x: -props.initialX * props.zoom,
    y: -props.initialY * props.zoom,
}));

const viewUrl = computed(() => withPrefix(`/published/workflow?id=${props.id}`));
</script>

<template>
    <div id="columns" class="d-flex">
        <ActivityBar v-if="!props.embed && showActivityBar" />
        <FlexPanel v-if="!props.embed && showToolbox" side="left">
            <ToolPanel />
        </FlexPanel>

        <div id="center" class="container-root m-3 w-100 overflow-auto d-flex flex-column">
            <div v-if="loading">
                <Heading h1 separator size="xl">
                    <FontAwesomeIcon icon="fa-spinner" spin />
                    Loading Workflow
                </Heading>
            </div>
            <div v-else-if="errored">
                <Heading h1 separator size="xl"> Failed to load published Workflow </Heading>

                <b-alert v-if="errorMessage" show variant="danger">
                    {{ errorMessage }}
                </b-alert>
                <b-alert v-else show variant="danger"> Unknown Error </b-alert>
            </div>
            <div v-else-if="workflowInfo" class="published-workflow">
                <div class="workflow-preview d-flex flex-column">
                    <span
                        v-if="props.showHeading || props.showButtons"
                        class="d-flex w-100 flex-gapx-1 flex-wrap justify-content-end align-items-center mb-2">
                        <Heading v-if="props.showHeading" h1 separator inline size="xl" class="flex-grow-1 mb-0">
                            <span v-if="props.showAbout"> Workflow Preview </span>
                            <span v-else> {{ workflowInfo.name }} </span>
                        </Heading>

                        <span v-if="props.showButtons">
                            <b-button :to="downloadUrl" title="Download Workflow" variant="secondary" size="md">
                                <FontAwesomeIcon icon="fa-download" />
                                Download
                            </b-button>

                            <b-button
                                v-if="!props.embed"
                                :href="importUrl"
                                :disabled="userStore.isAnonymous"
                                :title="logInTitle('Import Workflow')"
                                data-description="workflow import"
                                target="_blank"
                                variant="secondary"
                                size="md">
                                <FontAwesomeIcon icon="fa-edit" />
                                Import
                            </b-button>

                            <b-button
                                v-if="!props.embed"
                                :to="runUrl"
                                :disabled="userStore.isAnonymous"
                                :title="logInTitle('Run Workflow')"
                                variant="primary"
                                size="md">
                                <FontAwesomeIcon icon="fa-play" />
                                Run
                            </b-button>

                            <b-button
                                v-if="props.embed"
                                :href="viewUrl"
                                target="blank"
                                variant="primary"
                                size="md"
                                class="view-button font-weight-bold">
                                <FontAwesomeIcon :icon="['gxd', 'galaxyLogo']" />
                                View In Galaxy
                            </b-button>
                        </span>
                    </span>

                    <b-card class="workflow-card">
                        <WorkflowGraph
                            v-if="workflow && datatypesMapper"
                            :steps="workflow.steps"
                            :datatypes-mapper="datatypesMapper"
                            :initial-position="initialPosition"
                            :show-minimap="props.showMinimap"
                            :show-zoom-controls="props.showZoomControls"
                            readonly />
                    </b-card>
                </div>

                <WorkflowInformation
                    v-if="props.showAbout && workflowInfo"
                    :workflow-info="workflowInfo"
                    :embedded="props.embed" />
            </div>
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

.container-root {
    container-type: inline-size;
}

.published-workflow {
    display: flex;
    flex-grow: 1;
    gap: 1rem;
    height: 100%;

    .workflow-preview {
        flex-grow: 1;

        .workflow-card {
            flex-grow: 1;
        }
    }

    &:deep(.workflow-information) {
        max-width: 500px;
        height: 100%;
    }
}

@container (max-width: 900px) {
    .published-workflow {
        flex-direction: column;
        height: unset;

        .workflow-preview {
            height: 450px;
        }

        &:deep(.workflow-information) {
            max-width: unset;
            height: unset;
        }
    }
}

.view-button {
    --fa-secondary-color: #{$brand-toggle};
    --fa-secondary-opacity: 1;
}
</style>
