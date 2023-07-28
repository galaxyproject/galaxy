<script setup lang="ts">
import { library } from "@fortawesome/fontawesome-svg-core";
import { faSpinner } from "@fortawesome/free-solid-svg-icons";
import { FontAwesomeIcon } from "@fortawesome/vue-fontawesome";
import axios, { type AxiosError } from "axios";
import { ref, watch } from "vue";

import { useDatatypesMapper } from "@/composables/datatypesMapper";
import type { Workflow } from "@/stores/workflowStore";
import { assertDefined } from "@/utils/assertions";

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
                axios.get(`/api/workflows/${id}/download`),
            ]);

            assertDefined(workflowInfoData.name);

            workflowInfo.value = workflowInfoData;
            workflow.value = fullWorkflow;
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
            <div v-else-if="workflowInfo">
                <Heading h1 separator>{{ workflowInfo.name }}</Heading>

                <WorkflowGraph
                    v-if="workflow && datatypesMapper"
                    :steps="workflow.steps"
                    :datatypes-mapper="datatypesMapper"
                    readonly></WorkflowGraph>
            </div>
        </template>
    </PublishedItem>
</template>
