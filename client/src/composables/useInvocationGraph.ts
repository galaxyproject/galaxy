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
import { storeToRefs } from "pinia";
import { computed, type Ref, ref, set } from "vue";

import { GalaxyApi } from "@/api";
import { fetchCollectionDetails } from "@/api/datasetCollections";
import { fetchDatasetDetails } from "@/api/datasets";
import { type InvocationStep, type StepJobSummary, type WorkflowInvocationElementView } from "@/api/invocations";
import { getContentItemState } from "@/components/History/Content/model/states";
import { isWorkflowInput } from "@/components/Workflow/constants";
import { fromSimple } from "@/components/Workflow/Editor/modules/model";
import { getWorkflowFull } from "@/components/Workflow/workflows.services";
import { useInvocationStore } from "@/stores/invocationStore";
import { type Step } from "@/stores/workflowStepStore";
import { type Workflow } from "@/stores/workflowStore";
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
    nodeText?: string | boolean;
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

export const statePlaceholders: Record<string, string> = {
    ok: "successful",
    error: "failed",
};

/** Only one job needs to be in one of these states for the graph step to be in that state */
const SINGLE_INSTANCE_STATES = ["error", "running", "paused", "deleting"];
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
    const stepsPopulated = ref(false);
    const storeId = computed(() => `invocation-${invocation.value.id}`);

    const lastStepsJobsSummary = ref<StepJobSummary[]>([]);
    const invocationStore = useInvocationStore();
    const { graphStepsByStoreId } = storeToRefs(invocationStore);

    /** The full invocation mapped onto the original workflow */
    const invocationGraph = ref<InvocationGraph | null>(null);

    /** The workflow that was invoked */
    const loadedWorkflow = ref<any>(null);

    const loading = ref(true);

    provideScopedWorkflowStores(storeId);

    async function loadInvocationGraph() {
        loading.value = true;

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
            const { data: stepsJobsSummary, error } = await GalaxyApi().GET(
                "/api/invocations/{invocation_id}/step_jobs_summary",
                {
                    params: { path: { invocation_id: invocation.value.id } },
                }
            );

            if (error) {
                rethrowSimple(error);
            }

            await updateSteps(stepsJobsSummary);

            // Load the invocation graph into the editor the first time
            if (!stepsPopulated.value) {
                invocationGraph.value!.steps = { ...steps.value };
                await fromSimple(storeId.value, invocationGraph.value as any);
                stepsPopulated.value = true;
            }
        } catch (e) {
            rethrowSimple(e);
        } finally {
            loading.value = false;
        }
    }

    /** Update the steps of the invocation graph with the step job summaries, or initialize the steps
     * if they haven't been populated yet.
     * @param stepsJobsSummary - The job summary for each step in the invocation
     * */
    async function updateSteps(stepsJobsSummary: StepJobSummary[]) {
        /** Initialize with the original steps of the workflow, else update the existing graph steps */
        const fullSteps: Record<string, Step | GraphStep> = !stepsPopulated.value
            ? { ...loadedWorkflow.value.steps }
            : steps.value;

        // for each step, store the state and status of jobs
        for (let i = 0; i < Object.keys(fullSteps).length; i++) {
            /** An invocation graph step (initialized with the original workflow step) */
            let graphStepFromWfStep;
            if (!steps.value[i]) {
                graphStepFromWfStep = { ...fullSteps[i] } as GraphStep;
            } else {
                graphStepFromWfStep = steps.value[i] as GraphStep;
            }

            /** The raw invocation step */
            const invocationStep = invocation.value.steps[i];

            // TODO: What if the state of something not in the stepsJobsSummary has changed? (e.g.: subworkflows...)
            /** if the steps have not been populated or the job states have changed, update the step */
            const updateNonInputStep =
                !stepsPopulated.value ||
                JSON.stringify(stepsJobsSummary) !== JSON.stringify(lastStepsJobsSummary.value);

            if (updateNonInputStep && !isWorkflowInput(graphStepFromWfStep.type)) {
                let invocationStepSummary: StepJobSummary | undefined;
                if (invocationStep) {
                    invocationStepSummary = stepsJobsSummary.find((stepJobSummary: StepJobSummary) => {
                        if (stepJobSummary.model === "ImplicitCollectionJobs") {
                            return stepJobSummary.id === invocationStep.implicit_collection_jobs_id;
                        } else {
                            return stepJobSummary.id === invocationStep.job_id;
                        }
                    });
                }
                updateStep(graphStepFromWfStep, invocationStep, invocationStepSummary);
            } else if (invocationStep && graphStepFromWfStep.nodeText === undefined) {
                await initializeGraphInput(graphStepFromWfStep, invocationStep);
            }

            // add the graph step to the steps object if it doesn't exist yet
            if (!steps.value[i]) {
                set(steps.value, i, graphStepFromWfStep);
            }

            // update the invocation store's graph steps object
            // TODO: Find a better way of doing this, instead of using two separate objects...?
            set(graphStepsByStoreId.value, storeId.value, steps.value);
        }

        lastStepsJobsSummary.value = stepsJobsSummary;
    }

    /**
     * Store the state, jobs and class for the graph step based on the invocation step and its job summary.
     * @param graphStep - Invocation graph step
     * @param invocationStep - The invocation step for the workflow step
     * @param invocationStepSummary - The step job summary for the invocation step (based on its job id)
     */
    function updateStep(
        graphStep: GraphStep,
        invocationStep: InvocationStep | undefined,
        invocationStepSummary: StepJobSummary | undefined
    ) {
        /** The new state for the graph step */
        let newState = graphStep.state;

        // there is an invocation step for this workflow step
        if (invocationStep) {
            /** The `populated_state` for this graph step. (This may or may not be used to
             * derive the `state` for this invocation graph step) */
            let populatedState;

            if (graphStep.type === "subworkflow") {
                // if the step is a subworkflow, get the populated state from the invocation step
                populatedState = invocationStep.state || undefined;

                /* TODO:
                    Note that subworkflows are often in the `scheduled` state regardless of whether
                    their output is successful or not. One good way to visually show if a subworkflow was
                    successful is to set `graphStep.state = subworkflow.output?.state`.
                */
            }

            // First, try setting the state of the graph step based on its jobs' states or the populated state
            else {
                if (invocationStepSummary) {
                    // the step is not a subworkflow, get the populated state from the invocation step summary
                    populatedState = invocationStepSummary.populated_state;

                    if (invocationStepSummary.states) {
                        const statesForThisStep = Object.keys(invocationStepSummary.states);
                        // set the state of the graph step based on the job states for this step
                        newState = getStepStateFromJobStates(statesForThisStep);
                    }
                    // now store the job states for this step in the graph step, if they changed since the last time
                    if (JSON.stringify(graphStep.jobs) !== JSON.stringify(invocationStepSummary.states)) {
                        set(graphStep, "jobs", invocationStepSummary.states);
                    }
                } else {
                    // TODO: There is no summary for this step's `job_id`; what does this mean?
                    newState = "waiting";
                }
            }

            // If the state still hasn't been set, set it based on the populated state
            if (!newState) {
                if (populatedState === "scheduled" || populatedState === "ready") {
                    newState = "queued";
                } else if (populatedState === "resubmitted") {
                    newState = "new";
                } else if (populatedState === "failed") {
                    newState = "error";
                } else if (populatedState === "deleting") {
                    newState = "deleted";
                } else if (populatedState && !["stop", "stopped"].includes(populatedState)) {
                    newState = populatedState as GraphStep["state"];
                }
            }
        }

        // there is no invocation step for this workflow step, it is probably queued
        else {
            newState = "queued";
        }

        // if the state has changed, update the graph step
        if (graphStep.state !== newState) {
            graphStep.state = newState;
            setHeaderClass(graphStep);
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
                if (state === "deleting") {
                    return "deleted";
                }
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

    function setHeaderClass(graphStep: GraphStep) {
        /** Setting the header class for the graph step */
        graphStep.headerClass = getHeaderClass(graphStep.state as string);

        /** Setting the header icon for the graph step */
        if (graphStep.state) {
            graphStep.headerIcon = iconClasses[graphStep.state]?.icon;
            graphStep.headerIconSpin = iconClasses[graphStep.state]?.spin;
        }
    }

    async function initializeGraphInput(graphStep: GraphStep, invocationStep: InvocationStep) {
        const inputItem = invocation.value.inputs[graphStep.id];
        const inputParam = getWorkflowInputParam(invocation.value, invocationStep);
        if (inputItem && inputItem?.id !== undefined && inputItem?.id !== null) {
            if (inputItem.src === "hda") {
                const hda = await fetchDatasetDetails({ id: inputItem.id });
                // TODO: There is a type mismatch for `hda.state` and `GraphStep["state"]`
                set(graphStep, "state", getContentItemState(hda));
                set(graphStep, "nodeText", `${hda.hid}: <b>${hda.name}</b>`);
            } else {
                const hdca = await fetchCollectionDetails({ id: inputItem.id });
                // TODO: Same type mismatch as above
                set(graphStep, "state", getContentItemState(hdca));
                set(graphStep, "nodeText", `${hdca.hid}: <b>${hdca.name}</b>`);
            }
        } else if (inputParam) {
            if (typeof inputParam.parameter_value === "boolean") {
                set(graphStep, "nodeText", inputParam.parameter_value);
            } else {
                set(graphStep, "nodeText", `<b>${inputParam.parameter_value}</b>`);
            }
        }
        setHeaderClass(graphStep);
    }

    function getWorkflowInputParam(invocation: WorkflowInvocationElementView, invocationStep: InvocationStep) {
        return Object.values(invocation.input_step_parameters).find(
            (param) => param.workflow_step_id === invocationStep.workflow_step_id
        );
    }

    return {
        /** An id used to scope the store to the invocation's id */
        storeId,
        /** The steps of the invocation graph */
        steps,
        /** Fetches the original workflow structure (once) and the step job summaries for each step in the invocation,
         * and displays the job states on the workflow graph steps.
         */
        loadInvocationGraph,
        loading,
    };
}

export function getHeaderClass(state: string) {
    return {
        "node-header-invocation": true,
        [`header-${state}`]: !!state,
    };
}
