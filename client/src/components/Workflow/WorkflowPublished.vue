<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faBuilding, faDownload, faEdit, faPlay, faSpinner, faUser } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import axios, { type AxiosError } from "axios";
import { computed, onUnmounted, ref, watch } from "vue";

import { useDatatypesMapper } from "@/composables/datatypesMapper";
import { usePanels } from "@/composables/usePanels";
import { useUserStore } from "@/stores/userStore";
import { useConnectionStore } from "@/stores/workflowConnectionStore";
import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import { useWorkflowStepStore } from "@/stores/workflowStepStore";
import type { Workflow } from "@/stores/workflowStore";
import { assertDefined } from "@/utils/assertions";
import { withPrefix } from "@/utils/redirect";

import { fromSimple } from "./Editor/modules/model";

import WorkflowGraph from "./Editor/WorkflowGraph.vue";
import ActivityBar from "@/components/ActivityBar/ActivityBar.vue";
import Heading from "@/components/Common/Heading.vue";
import License from "@/components/License/License.vue";
import FlexPanel from "@/components/Panels/FlexPanel.vue";
import ToolBox from "@/components/Panels/ProviderAwareToolBox.vue";
import StatelessTags from "@/components/TagsMultiselect/StatelessTags.vue";
import UtcDate from "@/components/UtcDate.vue";

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

const connectionsStore = useConnectionStore();
const stepStore = useWorkflowStepStore();
const stateStore = useWorkflowStateStore();

stateStore.setScale(0.75);

onUnmounted(() => {
    connectionsStore.$reset();
    stepStore.$reset();
    stateStore.$reset();
});

watch(
    () => props.id,
    async (id) => {
        workflowInfo.value = undefined;
        loading.value = true;
        errored.value = false;
        errorMessage.value = "";

        try {
            const [{ data: workflowInfoData }, { data: fullWorkflow }] = await Promise.all([
                axios.get(`/api/workflows/${id}`),
                axios.get(`/workflow/load_workflow?_=true&id=${id}`),
            ]);

            assertDefined(workflowInfoData.name);

            workflowInfo.value = workflowInfoData;
            workflow.value = fullWorkflow;

            fromSimple(fullWorkflow);
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

const gravatarSource = computed(
    () => `https://secure.gravatar.com/avatar/${workflowInfo.value?.email_hash}?d=identicon`
);

const publishedByUser = computed(() => `/workflows/list_published?f-username=${workflowInfo.value?.owner}`);

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
            <ToolBox />
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

                <aside class="workflow-information">
                    <hgroup>
                        <Heading h2 size="xl" class="mb-0">About This Workflow</Heading>
                        <span class="ml-2">{{ workflowInfo.name }} - Version {{ workflowInfo.version }}</span>
                    </hgroup>

                    <div class="workflow-info-box">
                        <hgroup class="mb-2">
                            <Heading h3 size="md" class="mb-0">Author</Heading>
                            <span class="ml-2">{{ workflowInfo.owner }}</span>
                        </hgroup>

                        <img alt="User Avatar" :src="gravatarSource" class="mb-2" />

                        <router-link :to="publishedByUser">
                            All published Workflows by {{ workflowInfo.owner }}
                        </router-link>
                    </div>

                    <div v-if="workflow?.creator" class="workflow-info-box">
                        <Heading h3 size="md" class="mb-0">Creators</Heading>

                        <ul class="list-unstyled mb-0">
                            <li v-for="(creator, index) in workflow.creator" :key="index">
                                <FontAwesomeIcon v-if="creator.class === 'Person'" icon="fa-user" />
                                <FontAwesomeIcon v-if="creator.class === 'Organization'" icon="fa-building" />
                                {{ creator.name }}
                            </li>
                        </ul>
                    </div>

                    <div class="workflow-info-box">
                        <Heading h3 size="md" class="mb-0">Description</Heading>

                        <p v-if="workflowInfo.annotation" class="mb-0">
                            {{ workflowInfo.annotation }}
                        </p>
                        <p v-else class="mb-0">This Workflow has no description.</p>
                    </div>

                    <div v-if="workflowInfo?.tags" class="workflow-info-box">
                        <Heading h3 size="md" class="mb-0">Tags</Heading>

                        <StatelessTags class="tags mt-2" :value="workflowInfo.tags" disabled />
                    </div>

                    <div class="workflow-info-box">
                        <Heading h3 size="md" class="mb-0">License</Heading>

                        <License v-if="workflowInfo.license" :license-id="workflowInfo.license" />
                        <span v-else>No License specified</span>
                    </div>

                    <div class="workflow-info-box">
                        <Heading h3 size="md" class="mb-0">Last Updated</Heading>

                        <UtcDate :date="workflowInfo.update_time" mode="pretty" />
                    </div>
                </aside>
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

    aside {
        max-width: 500px;
        height: 100%;
    }

    @media only screen and (max-width: 1100px) {
        flex-direction: column;
        height: unset;

        .workflow-preview {
            height: 450px;
        }

        aside {
            max-width: unset;
            height: unset;
        }
    }
}

.workflow-information {
    flex-grow: 1;
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    align-items: start;
    justify-content: start;
    align-self: flex-start;
    overflow-y: scroll;

    .workflow-info-box {
        display: flex;
        flex-direction: column;
        align-items: start;
    }
}
</style>
