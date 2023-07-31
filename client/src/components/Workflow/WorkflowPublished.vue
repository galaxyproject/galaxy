<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import axios, { type AxiosError } from "axios";
import { onUnmounted, ref, watch } from "vue";

import { useDatatypesMapper } from "@/composables/datatypesMapper";
import { useConnectionStore } from "@/stores/workflowConnectionStore";
import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import { useWorkflowStepStore } from "@/stores/workflowStepStore";
import type { Workflow } from "@/stores/workflowStore";
import { assertDefined } from "@/utils/assertions";

import { fromSimple } from "./Editor/modules/model";

import WorkflowGraph from "./Editor/WorkflowGraph.vue";
import Heading from "@/components/Common/Heading.vue";
import PublishedItem from "@/components/Common/PublishedItem.vue";

library.add(faSpinner);

const props = defineProps<{
    id: string;
}>();

const workflowInfo = ref<
    | {
          name: string;
          [key: string]: unknown;
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

stateStore.setScale(0.5);

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
</script>

<template>
    <PublishedItem :item="workflowInfo">
        <template v-slot>
            <div v-if="loading">
                <Heading h1 separator>
                    <FontAwesomeIcon icon="fa-spinner" spin />
                    Loading Workflow
                </Heading>
            </div>
            <div v-else-if="errored">
                <Heading h1 separator> Failed to load published Workflow </Heading>

                <b-alert v-if="errorMessage" show variant="danger">
                    {{ errorMessage }}
                </b-alert>
                <b-alert v-else show variant="danger"> Unknown Error </b-alert>
            </div>
            <div v-else-if="workflowInfo" class="d-flex flex-column">
                <Heading h1 separator>{{ workflowInfo.name }}</Heading>

                <WorkflowGraph
                    v-if="workflow && datatypesMapper"
                    :steps="workflow.steps"
                    :datatypes-mapper="datatypesMapper"
                    readonly />
            </div>
        </template>
    </PublishedItem>
</template>
