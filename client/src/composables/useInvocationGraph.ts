import { type IconDefinition, library } from "@fortawesome/fontawesome-svg-core";
import {
    faCheckCircle,
    faClock,
    faExclamationTriangle,
    faForward,
    faPause,
    faSpinner,
    faTrash,
} from "@fortawesome/free-solid-svg-icons";
import Vue, { computed, type Ref, ref } from "vue";

import { stepJobsSummaryFetcher, type StepJobSummary, type WorkflowInvocationElementView } from "@/api/invocations";
import { isWorkflowInput } from "@/components/Workflow/constants";
import { fromSimple } from "@/components/Workflow/Editor/modules/model";
import { getWorkflowFull } from "@/components/Workflow/workflows.services";
import type { Step } from "@/stores/workflowStepStore";
import type { Workflow } from "@/stores/workflowStore";
import { rethrowSimple } from "@/utils/simple-error";

import { provideScopedWorkflowStores } from "./workflowStores";

export interface GraphStep extends Step {
    state?:
        | "new"
        | "upload"
        | "waiting"
        | "queued"
        | "running"
        | "ok"
        | "error"
        | "deleted"
        | "hidden"
        | "setting_metadata"
        | "paused"
        | "skipped";
    jobs: StepJobSummary["states"];
    headerClass?: Record<string, boolean>;
    headerIcon?: IconDefinition;
    headerIconSpin?: boolean;
}
interface InvocationGraph extends Workflow {
    steps: { [index: number]: GraphStep };
}

/** Classes for states' icons */
export const iconClasses: Record<string, { icon: IconDefinition; spin?: boolean; class?: string }> = {
    ok: { icon: faCheckCircle, class: "text-success" },
    error: { icon: faExclamationTriangle, class: "text-danger" },
    paused: { icon: faPause, class: "text-primary" },
    running: { icon: faSpinner, spin: true },
    new: { icon: faClock },
    waiting: { icon: faClock },
    queued: { icon: faClock },
    deleted: { icon: faTrash, class: "text-danger" },
    skipped: { icon: faForward, class: "text-warning" },
};

/** Only one job needs to be in one of these states for the graph step to be in that state */
const SINGLE_INSTANCE_STATES = ["error", "running", "paused"];
/** All jobs need to be in one of these states for the graph step to be in that state */
const ALL_INSTANCES_STATES = ["deleted", "skipped", "new", "queued"];

/** Composable that creates a readonly invocation graph and loads it onto a workflow editor canvas for display.
 * @param invocation - The invocation to display in graph view
 * @param workflowId - The id of the workflow that was invoked
 */
export function useInvocationGraph(
    invocation: Ref<WorkflowInvocationElementView>,
    workflowId: string | undefined,
    workflowVersion: number | undefined
) {
    library.add(faCheckCircle, faClock, faExclamationTriangle, faForward, faPause, faSpinner, faTrash);

    const steps = ref<{ [index: string]: GraphStep }>({});
    const storeId = computed(() => `invocation-${invocation.value.id}`);

    /** The full invocation mapped onto the original workflow */
    const invocationGraph = ref<InvocationGraph | null>(null);

    /** The workflow that was invoked */
    const loadedWorkflow = ref<any>(null);

    provideScopedWorkflowStores(storeId);

    async function loadInvocationGraph() {
        try {
            if (!workflowId) {
                throw new Error("Workflow Id is not defined");
            }
            if (workflowVersion === undefined) {
                throw new Error("Workflow Version is not defined");
            }

            // initialize the original full workflow and invocation graph refs (only on the first load)
            if (!loadedWorkflow.value) {
                loadedWorkflow.value = await getWorkflowFull(workflowId, workflowVersion);
            }
            if (!invocationGraph.value) {
                invocationGraph.value = {
                    ...loadedWorkflow.value,
                    id: storeId.value,
                    steps: null,
                };
            }

            // get the job summary for each step in the invocation
            const { data: stepJobsSummary } = await stepJobsSummaryFetcher({ invocation_id: invocation.value.id });

            /** The original steps of the workflow */
            const originalSteps: Record<string, Step> = { ...loadedWorkflow.value.steps };

            // for each step in the workflow, store the state and status of jobs
            for (let i = 0; i < Object.keys(originalSteps).length; i++) {
                /** An invocation graph step */
                const graphStepFromWfStep = { ...originalSteps[i] } as GraphStep;

                /** The type of the step (subworkflow, input, tool, etc.) */
                let type;
                if (graphStepFromWfStep.type === "subworkflow") {
                    type = "subworkflow";
                } else if (isWorkflowInput(graphStepFromWfStep.type)) {
                    type = "input";
                }

                /** The raw invocation step */
                const invocationStep = invocation.value.steps[i];

                if (type !== "input") {
                    // there is an invocation step for this workflow step
                    if (invocationStep) {
                        /** The `populated_state` for this graph step. (This may or may not be used to
                         * derive the `state` for this invocation graph step) */
                        let populatedState;

                        if (type === "subworkflow") {
                            // if the step is a subworkflow, get the populated state from the invocation step
                            populatedState = invocationStep.state || undefined;

                            /* TODO:
                                Note that subworkflows are often in the `scheduled` state regardless of whether
                                their output is successful or not. One good way to visually show if a subworkflow was
                                successful is to set `graphStepFromWfStep.state = subworkflow.output?.state`.
                            */
                        }

                        // First, try setting the state of the graph step based on its jobs' states or the populated state
                        else {
                            /** The step job summary for the invocation step (based on its job id) */
                            const invocationStepSummary = stepJobsSummary.find((stepJobSummary: StepJobSummary) => {
                                if (stepJobSummary.model === "ImplicitCollectionJobs") {
                                    return stepJobSummary.id === invocationStep.implicit_collection_jobs_id;
                                } else {
                                    return stepJobSummary.id === invocationStep.job_id;
                                }
                            });

                            if (invocationStepSummary) {
                                // the step is not a subworkflow, get the populated state from the invocation step summary
                                populatedState = invocationStepSummary.populated_state;

                                if (invocationStepSummary.states) {
                                    const statesForThisStep = Object.keys(invocationStepSummary.states);
                                    // set the state of the graph step based on the job states for this step
                                    graphStepFromWfStep.state = getStepStateFromJobStates(statesForThisStep);
                                }
                                // now store the job states for this step in the graph step
                                graphStepFromWfStep.jobs = invocationStepSummary.states;
                            } else {
                                // TODO: There is no summary for this step's `job_id`; what does this mean?
                                graphStepFromWfStep.state = "waiting";
                            }
                        }

                        // If the state still hasn't been set, set it based on the populated state
                        if (!graphStepFromWfStep.state) {
                            if (populatedState === "scheduled" || populatedState === "ready") {
                                graphStepFromWfStep.state = "queued";
                            } else if (populatedState === "resubmitted") {
                                graphStepFromWfStep.state = "new";
                            } else if (populatedState === "failed") {
                                graphStepFromWfStep.state = "error";
                            } else if (populatedState === "deleting") {
                                graphStepFromWfStep.state = "deleted";
                            } else if (populatedState && !["stop", "stopped"].includes(populatedState)) {
                                graphStepFromWfStep.state = populatedState as GraphStep["state"];
                            }
                        }
                    }

                    // there is no invocation step for this workflow step, it is probably queued
                    else {
                        graphStepFromWfStep.state = "queued";
                    }

                    /** Setting the header class for the graph step */
                    graphStepFromWfStep.headerClass = {
                        "node-header-invocation": true,
                        [`header-${graphStepFromWfStep.state}`]: !!graphStepFromWfStep.state,
                    };
                    // TODO: maybe a different one for inputs? Currently they have no state either.

                    /** Setting the header icon for the graph step */
                    if (graphStepFromWfStep.state) {
                        graphStepFromWfStep.headerIcon = iconClasses[graphStepFromWfStep.state]?.icon;
                        graphStepFromWfStep.headerIconSpin = iconClasses[graphStepFromWfStep.state]?.spin;
                    }
                }

                // update the invocation graph steps object
                Vue.set(steps.value, i, graphStepFromWfStep);
            }

            invocationGraph.value!.steps = { ...steps.value };

            // Load the invocation graph into the editor every time
            await fromSimple(storeId.value, invocationGraph.value as any);
        } catch (e) {
            rethrowSimple(e);
        }
    }

    /** Given the job states for a step, if the states fall into a single instance state
     * or all instances state, return the state of the step.
     * @param jobStates - The job states for a step
     * @returns The state for the graph step or `undefined` if the states don't match any
     *          single instance state or all instances state
     * */
    function getStepStateFromJobStates(jobStates: string[]): GraphStep["state"] | undefined {
        for (const state of SINGLE_INSTANCE_STATES) {
            if (jobStates.includes(state)) {
                return state as GraphStep["state"];
            }
        }
        for (const state of ALL_INSTANCES_STATES) {
            if (jobStates.every((jobState) => jobState === state)) {
                return state as GraphStep["state"];
            }
        }
        return undefined;
    }

    // TODO: Maybe we can use this to layout the graph after the steps are loaded (for neatness)?
    // async function layoutGraph() {
    //     const newSteps = await autoLayout(storeId.value, steps.value);
    //     if (newSteps) {
    //         newSteps?.map((step: any) => stepStore.updateStep(step));
    //         // Object.assign(steps.value, {...steps.value, ...stepStore.steps});
    //         Object.keys(steps.value).forEach((key) => {
    //             steps.value[key] = { ...steps.value[key], ...(stepStore.steps[key] as GraphStep) };
    //         });
    //     }
    //     invocationGraph.value!.steps = steps.value;
    //     await fromSimple(storeId.value, invocationGraph.value as any);
    // }

    return {
        /** An id used to scope the store to the invocation's id */
        storeId,
        /** The steps of the invocation graph */
        steps,
        /** Fetches the original workflow structure (once) and the step job summaries for each step in the invocation,
         * and displays the job states on the workflow graph steps.
         */
        loadInvocationGraph,
    };
}
