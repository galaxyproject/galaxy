<script setup lang="ts">
import axios, { type AxiosError, AxiosResponse } from "axios";
import { computed, ref, watch } from "vue";

import { components } from "@/api/schema";
import { fromSimple } from "@/components/Workflow/Editor/modules/model";
import { useDatatypesMapper } from "@/composables/datatypesMapper";
import { provideScopedWorkflowStores } from "@/composables/workflowStores";
import { useJobStore } from "@/stores/jobStore";
import type { WorkflowComment } from "@/stores/workflowEditorCommentStore";
import { type OutputTerminalSource, type Step } from "@/stores/workflowStepStore";
import type { Workflow } from "@/stores/workflowStore";
import { withPrefix } from "@/utils/redirect";

// import { autoLayout } from "../Editor/modules/layout";
import LoadingSpan from "@/components/LoadingSpan.vue";
import WorkflowGraph from "@/components/Workflow/Editor/WorkflowGraph.vue";

const TERMINAL_JOB_STATES = ["error", "deleted", "paused"];

type StepJobSummary =
    | components["schemas"]["InvocationStepJobsResponseStepModel"]
    | components["schemas"]["InvocationStepJobsResponseJobModel"]
    | components["schemas"]["InvocationStepJobsResponseCollectionJobsModel"];
type InvocationStep = components["schemas"]["InvocationStep"];
type InvocationStepOutput = components["schemas"]["InvocationStepOutput"];
type InvocationStepCollectionOutput = components["schemas"]["InvocationStepCollectionOutput"];
type Outputs = {
    [key: string]: InvocationStepOutput | InvocationStepCollectionOutput;
};

interface GraphStep extends Step {
    invocation_outputs: Outputs;
    state?: components["schemas"]["InvocationStepState"] | components["schemas"]["JobState"] | "terminal";
    jobs: StepJobSummary["states"];
}

const props = defineProps({
    invocation: {
        type: Object,
        required: true,
    },
    zoom: {
        type: Number,
        default: 0.75,
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

const workflow = ref<Workflow | null>(null);

const loading = ref(true);
const errored = ref(false);
const errorMessage = ref("");
const steps = ref<{ [index: string]: GraphStep }>({});
const comments = ref<WorkflowComment[]>([]);

const { datatypesMapper } = useDatatypesMapper();

/** an id used to scope the store to the invocation's id */
const storeId = computed(() => `invocation-${props.invocation.id}`);

const { stateStore } = provideScopedWorkflowStores(storeId);
const jobStore = useJobStore();

watch(
    () => props.zoom,
    () => (stateStore.scale = props.zoom),
    { immediate: true }
);

watch(
    () => props.workflowId,
    async (wfId: string) => {
        loading.value = true;
        errored.value = false;
        errorMessage.value = "";

        try {
            const { data: stepJobsSummaryData } = await axios.get(
                withPrefix(`/api/invocations/${props.invocation.id}/step_jobs_summary`)
            );
            const stepJobsSummary: StepJobSummary[] = stepJobsSummaryData;

            const { data: loadedWorkflow } = await axios.get(withPrefix(`/workflow/load_workflow?_=true&id=${wfId}`));
            workflow.value = loadedWorkflow;

            /** the steps for the workflow invoked */
            const originalSteps: Record<string, Step> = { ...loadedWorkflow.steps };

            for (let i = 0; i < Object.keys(originalSteps).length; i++) {
                const graphStepFromWfStep = { ...originalSteps[i], invocation_outputs: {} } as GraphStep;

                const invocationStep = stepJobsSummary[i];
                if (invocationStep) {
                    /** There is an invocation step for this workflow step */

                    // get full invocation step
                    // const { data: invocationStep }: AxiosResponse<InvocationStep> = await axios.get(
                    //     withPrefix(`/api/invocations/steps/${props.invocation.steps[i].id}`)
                    // );

                    // if (
                    //     ["scheduled", "cancelled", "failed"].includes(invocationStep.state as string) &&
                    //     invocationStep.jobs?.length && invocationStep.jobs?.length > 0 &&
                    //     invocationStep.jobs.every((job: any) => TERMINAL_JOB_STATES.includes(job.state))
                    // ) {
                    //     graphStepFromWfStep.state = "terminal";

                    //     // TODO: maybe only 1 job is fine?
                    //     // for each job in invocationStep.jobs, get the job details and add them to the graphStep
                    //     for (const job of invocationStep.jobs) {
                    //         if (!jobStore.getJob(job.id)) {
                    //             await jobStore.fetchJob(job.id);
                    //         }
                    //         const jobDetails = jobStore.getJob(job.id);
                    //         if (jobDetails) {
                    //             if (!graphStepFromWfStep.jobs) {
                    //                 graphStepFromWfStep.jobs = [];
                    //             }
                    //             graphStepFromWfStep.jobs?.push(jobDetails as any); // TODO: fix typing
                    //         }
                    //     }

                    //     // console.log("Step", i, "is terminal", invocationStep.state, invocationStep.jobs);
                    // } else if (invocationStep.state === "scheduled") {
                    //     graphStepFromWfStep.state = "ok";
                    //     // console.log("Step", i, "is ok", invocationStep.state);
                    // } else {
                    //     graphStepFromWfStep.state = invocationStep.state || 'ok';
                    //     // console.log("Step", i, "is not terminal", invocationStep.state);
                    // }

                    if (invocationStep.states && Object.keys(invocationStep.states).includes("error")) {
                        graphStepFromWfStep.state = "error";
                    } else if (!invocationStep.states) {
                        graphStepFromWfStep.state = invocationStep.populated_state;
                    }

                    graphStepFromWfStep.jobs = invocationStep.states;
                    // for each output of the workflow step, get the corresponding output of the invocation step
                    // graphStepFromWfStep?.outputs?.forEach((output: OutputTerminalSource, _) => {
                    //     let currInvOutput;
                    //     const collectionOutput = invocationStep.output_collections?.[output.name];
                    //     if (collectionOutput && (("collection" in output && output.collection) || collectionOutput.src === "hdca")) {
                    //         currInvOutput = collectionOutput;
                    //     } else if ("parameter" in output && output.parameter) {
                    //         // TODO: deal with this case
                    //     } else if (invocationStep.outputs) {
                    //         currInvOutput = invocationStep.outputs[output.name];
                    //     }

                    //     // if there is an output for this invocation step
                    //     if (currInvOutput) {
                    //         // add the invocation output to the current invocation graph step
                    //         graphStepFromWfStep.invocation_outputs[output.name] = currInvOutput;
                    //     } else if (!output.optional) {
                    //         // there is no output for this invocation step, and it is not optional
                    //         // graphStepFromWfStep.state = "error";

                    //         // // TODO: This probably doesn't belong here
                    //         // const commentContent = `Step ${i} did not create output ${output.name}.`;
                    //         // console.log("Position etc.", graphStepFromWfStep.position, graphStepFromWfStep);
                    //         // const currentComment: MarkdownWorkflowComment = {
                    //         //     id: comments.value.length,
                    //         //     position: [200, 200],
                    //         //     size: [200, 200],
                    //         //     type: "markdown",
                    //         //     color: "red",
                    //         //     data: { text: `Failure.\n\n\n ${commentContent}` },
                    //         // };
                    //         // comments.value.push(currentComment);
                    //     }
                    // });
                } else {
                    graphStepFromWfStep.state = "scheduled";
                    // /** There is no invocation step for this workflow step,
                    //  * so... TODO: create an errored step / place a comment?
                    //  */
                    // graphStepFromWfStep.state = "error";
                    // const commentContent = `Step ${i} was not executed.`;
                    // const currentComment: MarkdownWorkflowComment = {
                    //     id: comments.value.length,
                    //     position: [200, 200],
                    //     size: [200, 200],
                    //     type: "markdown",
                    //     color: "red",
                    //     data: { text: `Failure.\n\n\n ${commentContent}` },
                    // };
                    // comments.value.push(currentComment);
                }
                steps.value[i] = graphStepFromWfStep;
            }

            console.log("Steps", steps.value);
            const fullInvocation = {
                steps: steps.value as any, // TODO: fix typing
                comments: comments.value, // TODO: what about original WF comments
            };

            // load invocation graph onto the canvas
            await fromSimple(storeId.value, fullInvocation);

            // // organize the graph
            // await layoutGraph(); // TODO: not working,
        } catch (e) {
            const error = e as AxiosError<{ err_msg?: string }>;
            console.error(e);

            if (error.response?.data.err_msg) {
                errorMessage.value = error.response.data.err_msg;
            } else {
                errorMessage.value = e as string;
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

const initialPosition = computed(() => ({
    x: -props.initialX * props.zoom,
    y: -props.initialY * props.zoom,
}));

// async function layoutGraph() {
//     const newSteps = await autoLayout(storeId.value, steps.value);
//     if (newSteps) {
//         newSteps?.map((step: any) => stepStore.updateStep(step));
//     }
// }
</script>

<template>
    <div id="center" class="container-root m-3 w-100 overflow-auto d-flex flex-column">
        <b-alert v-if="loading" show variant="info">
            <LoadingSpan message="Loading Invocation Graph" />
        </b-alert>
        <div v-else-if="errored">
            <b-alert v-if="errorMessage" show variant="danger">
                {{ errorMessage }}
            </b-alert>
            <b-alert v-else show variant="danger"> Unknown Error </b-alert>
        </div>
        <div v-else-if="workflow && datatypesMapper" class="workflow-invocation">
            <div class="workflow-preview d-flex flex-column">
                <b-card class="workflow-card">
                    <WorkflowGraph
                        :steps="steps"
                        :datatypes-mapper="datatypesMapper"
                        :initial-position="initialPosition"
                        :show-minimap="props.showMinimap"
                        :show-zoom-controls="props.showZoomControls"
                        invocation
                        readonly />
                </b-card>
            </div>
        </div>
    </div>
</template>

<style scoped lang="scss">
@import "theme/blue.scss";

.container-root {
    container-type: inline-size;
}

.workflow-invocation {
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
}

@container (max-width: 900px) {
    .workflow-invocation {
        flex-direction: column;
        height: unset;

        .workflow-preview {
            height: 450px;
        }
    }
}
</style>
