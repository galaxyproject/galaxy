import type { IconDefinition } from "@fortawesome/fontawesome-svg-core";
import {
    faCheckCircle,
    faClock,
    faCloud,
    faExclamationTriangle,
    faForward,
    faPause,
    faQuestionCircle,
    faSpinner,
    faStopCircle,
    faTrash,
} from "@fortawesome/free-solid-svg-icons";
import { computed, type Ref, ref, watch } from "vue";

import { fetchCollectionSummary } from "@/api/datasetCollections";
import { fetchDatasetDetails } from "@/api/datasets";
import type { InvocationStep, StepJobSummary, WorkflowInvocationElementView } from "@/api/invocations";
import type { components } from "@/api/schema";
import type { StoredWorkflowDetailed } from "@/api/workflows";
import { getContentItemState } from "@/components/History/Content/model/states";
import { isWorkflowInput } from "@/components/Workflow/constants";
import { fromSimple } from "@/components/Workflow/Editor/modules/model";
import type { ParameterOutput, Step } from "@/stores/workflowStepStore";
import { useWorkflowStore } from "@/stores/workflowStore";
import { rerunWhileBusy } from "@/utils/sharedPromise";
import { rethrowSimple } from "@/utils/simple-error";

import { provideScopedWorkflowStores } from "./workflowStores";

/** All possible states for an Invocation Graph step.
 * - `JobState`: for tool/collection steps (derived from job states and `populated_state`)
 * - `DatasetState`: for data input steps (derived from the dataset/collection state)
 * - `InvocationStepState`: for subworkflow steps (derived from the invocation step state)
 * - `"uninitialized"`: initial state before the step's actual state has been determined */
export type GraphStepState =
    | components["schemas"]["JobState"]
    | components["schemas"]["DatasetState"]
    | components["schemas"]["InvocationStepState"]
    | "uninitialized";

export interface GraphStep extends Step {
    state: GraphStepState;
    jobs: StepJobSummary["states"];
    headerClass?: Record<string, boolean>;
    headerIcon?: IconDefinition;
    headerIconSpin?: boolean;
    nodeText?: string | boolean;
}
interface InvocationGraph extends Omit<StoredWorkflowDetailed, "steps"> {
    steps: { [index: number]: GraphStep };
}

/** Classes for states' icons */
export const iconClasses: Record<GraphStepState, { icon: IconDefinition; spin?: boolean; class?: string }> = {
    // terminal success
    ok: { icon: faCheckCircle, class: "text-success" },
    empty: { icon: faCheckCircle, class: "text-success" },
    // transitional / waiting
    new: { icon: faClock },
    waiting: { icon: faClock },
    queued: { icon: faClock },
    resubmitted: { icon: faClock },
    ready: { icon: faClock },
    scheduled: { icon: faClock },
    // active
    running: { icon: faSpinner, spin: true },
    upload: { icon: faSpinner, spin: true },
    setting_metadata: { icon: faSpinner, spin: true },
    // finishing brackets the metadata step, so it mirrors setting_metadata
    finishing: { icon: faSpinner, spin: true },
    // paused / info
    paused: { icon: faPause, class: "text-primary" },
    deferred: { icon: faCloud, class: "text-info" },
    // skipped
    skipped: { icon: faForward, class: "text-warning" },
    // errors / failures
    error: { icon: faExclamationTriangle, class: "text-danger" },
    failed: { icon: faExclamationTriangle, class: "text-danger" },
    failed_metadata: { icon: faExclamationTriangle, class: "text-danger" },
    discarded: { icon: faExclamationTriangle, class: "text-danger" },
    // deleted / stopped
    deleted: { icon: faTrash, class: "text-danger" },
    deleting: { icon: faTrash, class: "text-danger" },
    stop: { icon: faStopCircle, class: "text-danger" },
    stopped: { icon: faStopCircle, class: "text-danger" },
    // not yet determined
    uninitialized: { icon: faQuestionCircle },
};

export const statePlaceholders: Record<string, string> = {
    ok: "successful",
    error: "failed",
    upload: "uploading",
    setting_metadata: "setting metadata",
    failed_metadata: "have metadata errors",
    stop: "stopping",
};

/** Only one job needs to be in one of these states for the graph step to be in that state */
const SINGLE_INSTANCE_STATES: GraphStepState[] = ["error", "running", "paused", "deleting"];
/** All jobs need to be in one of these states for the graph step to be in that state */
const ALL_INSTANCES_STATES: GraphStepState[] = ["deleted", "skipped", "new", "queued"];

/** Composable that creates a readonly invocation graph and loads it onto a workflow editor canvas for display.
 * @param invocation - The invocation to display in graph view
 * @param workflowId - The id of the workflow that was invoked
 */
export function useInvocationGraph(
    invocation: Ref<WorkflowInvocationElementView>,
    stepsJobsSummary: Ref<StepJobSummary[]>,
    workflowId: Ref<string | undefined>,
    workflowVersion: Ref<number | undefined>,
) {
    const steps = ref<{ [index: string]: GraphStep }>({});
    const stepsPopulated = ref(false);
    const storeId = computed(() => `invocation-${invocation.value.id}`);

    /** The full invocation mapped onto the original workflow.
     * _(Needed to map the invocation onto the workflow editor graph.)_
     */
    const invocationGraph = ref<InvocationGraph | null>(null);

    /** The workflow that was invoked */
    const loadedWorkflow = ref<any>(null);

    const workflowStore = useWorkflowStore();

    const loading = ref(true);

    provideScopedWorkflowStores(storeId);

    /** Update the steps from the latest inputs; a poll landing mid-update makes it run again */
    const refreshSteps = rerunWhileBusy(async () => {
        if (stepsJobsSummary.value) {
            await updateSteps(stepsJobsSummary.value);
        }
    });

    // Follow the invocation and job summaries polled by the parent, once the workflow has loaded.
    watch([invocation, stepsJobsSummary], async () => {
        if (loadedWorkflow.value) {
            try {
                await refreshSteps();
            } catch (e) {
                console.error("Failed to update invocation graph steps", e);
            }
        }
    });

    /** Load the invocation graph and steps onto the editor canvas.
     * @param loadOntoEditor - If set to false, initializes graph steps but does not load them onto the editor.
     */
    async function loadInvocationGraph(loadOntoEditor = true) {
        loading.value = true;

        try {
            if (!workflowId.value) {
                throw new Error("Workflow Id is not defined");
            }
            if (workflowVersion.value === undefined) {
                throw new Error("Workflow Version is not defined");
            }

            // initialize the original full workflow and invocation graph refs (only on the first load)
            if (!loadedWorkflow.value) {
                loadedWorkflow.value = await workflowStore.getFullWorkflowCached(
                    workflowId.value,
                    workflowVersion.value,
                );
            }
            if (!invocationGraph.value) {
                invocationGraph.value = {
                    ...loadedWorkflow.value,
                    id: storeId.value,
                    steps: null,
                };
            }

            await refreshSteps();

            // Load the invocation graph into the editor the first time
            if (!stepsPopulated.value && loadOntoEditor) {
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
        const stepCount = Object.keys(fullSteps).length;
        const findStepJobSummary = stepJobSummaryLookup(stepsJobsSummary);
        /** The first failed input fetch, thrown once all other steps are updated */
        let inputError: Error | undefined;

        // for each step, store the state and status of jobs
        for (let i = 0; i < stepCount; i++) {
            /** An invocation graph step (initialized with the original workflow step) */
            let graphStepFromWfStep;
            if (!steps.value[i]) {
                graphStepFromWfStep = { ...fullSteps[i], state: "uninitialized" } as GraphStep;
                setHeaderClass(graphStepFromWfStep);
            } else {
                graphStepFromWfStep = steps.value[i] as GraphStep;
            }

            /** The raw invocation step */
            const invocationStep = invocation.value.steps[i];

            // `updateStep` only writes what changed, so unchanged steps don't re-render
            if (!isWorkflowInput(graphStepFromWfStep.type)) {
                updateStep(graphStepFromWfStep, invocationStep, invocationStep && findStepJobSummary(invocationStep));
            } else if (invocationStep && graphStepFromWfStep.nodeText === undefined) {
                try {
                    await initializeGraphInput(graphStepFromWfStep, invocationStep);
                } catch (e) {
                    // `nodeText` stays unset, so the next update retries this input
                    inputError ??= e as Error;
                }
            }

            // add the graph step to the steps object if it doesn't exist yet
            if (!steps.value[i]) {
                steps.value[i] = graphStepFromWfStep;
            }
        }

        if (inputError !== undefined) {
            throw inputError;
        }
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
        invocationStepSummary: StepJobSummary | undefined,
    ) {
        /** The resolved state for the graph step (undefined = not yet determined) */
        let newState: GraphStepState | undefined = undefined;

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
                        graphStep.jobs = invocationStepSummary.states;
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
                    newState = populatedState;
                }
            }
        }

        // there is no invocation step for this workflow step, it is probably queued
        else {
            newState = "queued";
        }

        // preserve previous state if a new one couldn't be determined
        const resolvedState = newState ?? graphStep.state;
        if (graphStep.state !== resolvedState) {
            graphStep.state = resolvedState;
            setHeaderClass(graphStep);
        }
    }

    /** Given the job states for a step, if the states fall into a single instance state
     * or all instances state, return the state of the step.
     * @param jobStates - The job states for a step
     * @returns The state for the graph step or `undefined` if the states don't match any
     *          single instance state or all instances state
     * */
    function getStepStateFromJobStates(jobStates: string[]): GraphStepState | undefined {
        for (const state of SINGLE_INSTANCE_STATES) {
            if (jobStates.includes(state)) {
                if (state === "deleting") {
                    return "deleted";
                }
                return state;
            }
        }
        for (const state of ALL_INSTANCES_STATES) {
            if (jobStates.every((jobState) => jobState === state)) {
                return state;
            }
        }
        return undefined;
    }

    function setHeaderClass(graphStep: GraphStep) {
        /** Setting the header class for the graph step */
        graphStep.headerClass = getHeaderClass(graphStep.state);

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
                graphStep.state = getContentItemState(hda) as GraphStep["state"];
                graphStep.nodeText = `${hda.hid}: <b>${hda.name}</b>`;
            } else {
                const hdca = await fetchCollectionSummary({ hdca_id: inputItem.id });
                // TODO: Same type mismatch as above
                graphStep.state = getContentItemState(hdca) as GraphStep["state"];
                graphStep.nodeText = `${hdca.hid}: <b>${hdca.name}</b>`;
            }
            setHeaderClass(graphStep);
        } else if (inputParam) {
            const parameterValue = inputParam.parameter_value;
            const parameterType = (graphStep.outputs[0] as ParameterOutput | undefined)?.type;
            if (typeof parameterValue === "boolean") {
                graphStep.nodeText = parameterValue;
            } else if (parameterType === "color" && typeof parameterValue === "string") {
                graphStep.nodeText = parameterValue;
            } else {
                graphStep.nodeText = `<b>${parameterValue}</b>`;
            }
        }
    }

    function getWorkflowInputParam(invocation: WorkflowInvocationElementView, invocationStep: InvocationStep) {
        return Object.values(invocation.input_step_parameters).find(
            (param) => param.workflow_step_id === invocationStep.workflow_step_id,
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

/** Index step job summaries once, for finding the summary of each invocation step.
 * @param stepsJobsSummary - The job summary for each step in the invocation
 * @returns A function that returns the job summary for an invocation step, if any
 */
export function stepJobSummaryLookup(stepsJobsSummary: StepJobSummary[]) {
    const jobSummaries = new Map<string, StepJobSummary>();
    const implicitCollectionJobsSummaries = new Map<string, StepJobSummary>();
    for (const summary of stepsJobsSummary) {
        const summaries = summary.model === "ImplicitCollectionJobs" ? implicitCollectionJobsSummaries : jobSummaries;
        if (!summaries.has(summary.id)) {
            summaries.set(summary.id, summary);
        }
    }
    return (invocationStep: InvocationStep): StepJobSummary | undefined =>
        (invocationStep.implicit_collection_jobs_id &&
            implicitCollectionJobsSummaries.get(invocationStep.implicit_collection_jobs_id)) ||
        (invocationStep.job_id ? jobSummaries.get(invocationStep.job_id) : undefined);
}

export function getHeaderClass(state: GraphStepState | undefined) {
    return {
        "node-header-invocation": true,
        [`header-${state}`]: !!state,
    };
}
