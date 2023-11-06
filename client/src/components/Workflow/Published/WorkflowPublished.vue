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

const props = defineProps<{
    id: string;
}>();

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

stateStore.setScale(0.75);

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
</script>

<template>
    <div id="columns" class="d-flex">
        <ActivityBar v-if="showActivityBar" />
        <FlexPanel v-if="showToolbox" side="left">
            <ToolPanel />
        </FlexPanel>

        <div id="center" class="m-3 w-100 overflow-auto d-flex flex-column">
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
                    <span class="d-flex w-100 flex-gapx-1 flex-wrap justify-content-center align-items-center mb-2">
                        <Heading h1 separator inline size="xl" class="flex-grow-1 mb-0">Workflow Preview</Heading>

                        <span>
                            <b-button :to="downloadUrl" title="Download Workflow" variant="secondary" size="md">
                                <FontAwesomeIcon icon="fa-download" />
                                Download
                            </b-button>

                            <b-button
                                :href="importUrl"
                                :disabled="userStore.isAnonymous"
                                :title="logInTitle('Import Workflow')"
                                data-description="workflow import"
                                target="blank"
                                variant="secondary"
                                size="md">
                                <FontAwesomeIcon icon="fa-edit" />
                                Import
                            </b-button>

                            <b-button
                                :to="runUrl"
                                :disabled="userStore.isAnonymous"
                                :title="logInTitle('Run Workflow')"
                                variant="primary"
                                size="md">
                                <FontAwesomeIcon icon="fa-play" />
                                Run
                            </b-button>
                        </span>
                    </span>

                    <b-card class="workflow-card">
                        <WorkflowGraph
                            v-if="workflow && datatypesMapper"
                            :steps="workflow.steps"
                            :datatypes-mapper="datatypesMapper"
                            readonly />
                    </b-card>
                </div>

                <WorkflowInformation v-if="workflowInfo" :workflow-info="workflowInfo" />
            </div>
        </div>
    </div>
</template>

<style scoped lang="scss">
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

    @media only screen and (max-width: 1100px) {
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
</style>
