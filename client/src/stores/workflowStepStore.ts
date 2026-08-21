import { computed, del, ref, set } from "vue";

import type { FieldDict, SampleSheetColumnDefinitions } from "@/api";
import { isWorkflowInput } from "@/components/Workflow/constants";
import type { CollectionTypeDescriptor } from "@/components/Workflow/Editor/modules/collectionTypeDescription";
import {
    BOOLEAN_GATE_INPUT_NAME,
    expressionReferencesInput,
} from "@/components/Workflow/Editor/modules/whenExpression";
import {
    type InputPath,
    resolveConnectionNameToInputPath,
} from "@/components/Workflow/Editor/modules/workflowInputPath";
import { getConnectionId, useConnectionStore } from "@/stores/workflowConnectionStore";
import { assertDefined } from "@/utils/assertions";

import { defineScopedStore } from "./scopedStore";
import { useWorkflowStateStore } from "./workflowEditorStateStore";
import type { Connection } from "./workflowStoreTypes";

interface StepPosition {
    top: number;
    left: number;
}

/*
      "ChangeDatatypeActionout_file1": {
        "action_type": "ChangeDatatypeAction",
        "output_name": "out_file1",
        "action_arguments": {
          "newtype": "ab1"
        }
      }
*/

export interface PostJobAction {
    action_type: string;
    output_name: string;
    action_arguments: {
        [index: string]: string;
    };
}

export interface PostJobActions {
    [index: string]: PostJobAction;
}

export interface DataOutput {
    valid?: boolean;
    extensions: string[];
    name: string;
    optional: boolean;
    type?: "data";
}

export interface CollectionOutput extends Omit<DataOutput, "type"> {
    collection: boolean;
    collection_type: string;
    collection_type_source: string | null;
}

export declare const ParameterTypes: "text" | "integer" | "float" | "boolean" | "color" | "data";
export interface ParameterOutput extends Omit<DataOutput, "type" | "extensions"> {
    type: typeof ParameterTypes;
    parameter: true;
    multiple: boolean;
}

interface BaseStepInput {
    valid?: boolean;
    name: string;
    label: string;
    multiple: boolean;
    extensions: string[];
    optional: boolean;
    input_type: string;
    input_subworkflow_step_id?: number;
}

export interface DataStepInput extends BaseStepInput {
    input_type: "dataset";
}

export interface DataCollectionStepInput extends BaseStepInput {
    input_type: "dataset_collection";
    collection_types: string[];
    fields: FieldDict[];
    column_definitions: SampleSheetColumnDefinitions;
}

export interface ParameterStepInput extends Omit<BaseStepInput, "input_type"> {
    input_type: "parameter";
    type: typeof ParameterTypes;
}

export type InputTerminalSource = DataStepInput | DataCollectionStepInput | ParameterStepInput;
export type OutputTerminalSource = DataOutput | CollectionOutput | ParameterOutput;
export type TerminalSource = InputTerminalSource | OutputTerminalSource;

interface WorkflowOutput {
    output_name: string;
    label?: string | null;
    uuid?: string | null;
}

export interface NewStep {
    annotation?: string;
    config_form?: { [index: string]: any };
    content_id?: string | null;
    id?: number;
    errors?: string[] | null;
    input_connections: StepInputConnection;
    inputs: Array<InputTerminalSource>;
    label?: string | null;
    name: string;
    outputs: Array<OutputTerminalSource>;
    position?: StepPosition;
    post_job_actions?: PostJobActions;
    tool_id?: string;
    tool_uuid?: string;
    tool_state: Record<string, unknown>;
    tool_version?: string;
    tooltip?: string | null;
    type: "tool" | "data_input" | "data_collection_input" | "subworkflow" | "parameter_input" | "pause" | "pick_value";
    uuid?: string;
    when?: string | null;
    workflow_id?: string;
    workflow_outputs?: WorkflowOutput[];
}

export interface Step extends NewStep {
    id: number;
}

export interface Steps {
    [index: string]: Step;
}

export interface StepInputConnection {
    [index: string]: ConnectionOutputLink | ConnectionOutputLink[] | undefined;
}

export interface ConnectionOutputLink {
    output_name: string;
    id: number;
    input_subworkflow_step_id?: number;
}

/** Normalize the persisted single-or-array connection shape for read-only traversal. */
export function normalizeConnectionOutputLinks(
    links: ConnectionOutputLink | ConnectionOutputLink[] | undefined,
): readonly ConnectionOutputLink[] {
    return Array.isArray(links) ? links : links ? [links] : [];
}

export interface WorkflowOutputs {
    [index: string]: {
        stepId: number;
        outputName: string;
    };
}

interface StepInputMapOver {
    [index: number]: { [index: string]: CollectionTypeDescriptor };
}

export type WorkflowStepStore = ReturnType<typeof useWorkflowStepStore>;

/**
 * Returns combined step inputs: extra inputs (e.g., "when" conditionals) followed by regular inputs.
 * This is the single source of truth for all step inputs.
 */
export function getCombinedStepInputs(step: Step, stepStore: WorkflowStepStore): InputTerminalSource[] {
    const extraInputs = stepStore.getStepExtraInputs(step.id);
    return [...extraInputs, ...step.inputs];
}

/**
 * True when the value arriving on this input can be absent at run time, either because
 * every source output is optional or because every source step is itself gated.
 */
export function connectedInputCanBeAbsent(step: Step, inputName: string, stepStore: WorkflowStepStore): boolean {
    const links = step.input_connections?.[inputName];
    if (!links) {
        return false;
    }
    const linkArray = normalizeConnectionOutputLinks(links);
    if (linkArray.length === 0) {
        return false;
    }
    return linkArray.every((link) => {
        const sourceStep = stepStore.getStep(link.id);
        if (!sourceStep) {
            return false;
        }
        if (sourceStep.when) {
            return true;
        }
        return Boolean(sourceStep.outputs.find((output) => output.name === link.output_name)?.optional);
    });
}

export const useWorkflowStepStore = defineScopedStore("workflowStepStore", (workflowId) => {
    const steps = ref<Steps>({});
    const stepMapOver = ref<{ [index: number]: CollectionTypeDescriptor }>({});
    const stepInputMapOver = ref<StepInputMapOver>({});
    const stepIndex = ref(-1);
    const stepExtraInputs = ref<{ [index: number]: InputTerminalSource[] }>({});

    function $reset() {
        steps.value = {};
        stepMapOver.value = {};
        stepInputMapOver.value = {};
        stepIndex.value = -1;
        stepExtraInputs.value = {};
    }

    const getStep = computed(() => (stepId: number) => steps.value[stepId.toString()]);

    const getStepExtraInputs = computed(() => (stepId: number) => stepExtraInputs.value[stepId] || []);

    const getStepIndex = computed(() =>
        Math.max(...Object.values(steps.value).map((step) => step.id), stepIndex.value),
    );

    const hasActiveOutputs = computed(() =>
        Boolean(Object.values(steps.value).find((step) => step.workflow_outputs?.length)),
    );

    const hasInputSteps = computed(() =>
        Boolean(Object.values(steps.value).find((step) => isWorkflowInput(step.type))),
    );

    const workflowOutputs = computed(() => {
        const workflowOutputs: WorkflowOutputs = {};

        Object.values(steps.value).forEach((step) => {
            if (step.workflow_outputs?.length) {
                step.workflow_outputs.forEach((workflowOutput) => {
                    if (workflowOutput.label) {
                        workflowOutputs[workflowOutput.label] = {
                            outputName: workflowOutput.output_name,
                            stepId: step.id,
                        };
                    }
                });
            }
        });

        return workflowOutputs;
    });

    const duplicateLabels = computed(() => {
        const duplicateLabels: Set<string> = new Set();
        const labels: Set<string> = new Set();

        Object.values(steps.value).forEach((step) => {
            if (step.workflow_outputs?.length) {
                step.workflow_outputs.forEach((workflowOutput) => {
                    if (workflowOutput.label) {
                        if (labels.has(workflowOutput.label)) {
                            duplicateLabels.add(workflowOutput.label);
                        }
                        labels.add(workflowOutput.label);
                    }
                });
            }
        });

        return duplicateLabels;
    });

    const connectionStore = useConnectionStore(workflowId);

    const stateStore = useWorkflowStateStore(workflowId);

    function addStep(newStep: NewStep, select = false, createConnections = true): Step {
        const stepId = newStep.id ?? getStepIndex.value + 1;
        const step = Object.freeze({ ...newStep, id: stepId } as Step);

        set(steps.value, stepId.toString(), step);

        if (createConnections) {
            stepToConnections(step).forEach((connection) => connectionStore.addConnection(connection));
        }

        refreshStepExtraInputs(step);
        refreshGatePortsReadingSource(step.id);

        if (select) {
            stateStore.setStepMultiSelected(step.id, true);
        }

        return step;
    }

    function insertNewStep(
        contentId: NewStep["content_id"],
        name: NewStep["name"],
        type: NewStep["type"],
        position: NewStep["position"],
    ) {
        const stepData: NewStep = {
            name: name,
            content_id: contentId,
            input_connections: {},
            type: type,
            inputs: [],
            outputs: [],
            position: position,
            post_job_actions: {},
            tool_state: {},
        };

        return addStep(stepData);
    }

    function updateStep(step: Step) {
        const previousStep = steps.value[step.id.toString()];
        const workflow_outputs = step.workflow_outputs?.filter((workflowOutput) =>
            step.outputs.find((output) => workflowOutput.output_name == output.name),
        );

        const updatedStep = Object.freeze({ ...step, workflow_outputs });
        steps.value[step.id.toString()] = updatedStep;
        refreshStepExtraInputs(updatedStep);

        // A probe terminal mirrors its source's effective output shape. Recompute
        // downstream gate ports only when that shape may have changed, so frequent
        // updates to unrelated fields (notably position) avoid a full workflow scan.
        if (!previousStep || gatePortSourceShapeChanged(previousStep, updatedStep)) {
            refreshGatePortsReadingSource(updatedStep.id);
        }
    }

    function refreshStepExtraInputs(step: Step) {
        stepExtraInputs.value[step.id] = findStepExtraInputs(step, steps.value);
    }

    function refreshGatePortsReadingSource(sourceStepId: number) {
        Object.values(steps.value).forEach((candidate) => {
            if (candidate.id !== sourceStepId && stepReadsSource(candidate, sourceStepId)) {
                refreshStepExtraInputs(candidate);
            }
        });
    }

    function updateStepValue<K extends keyof Step>(stepId: number, key: K, value: Step[K]) {
        const step = steps.value[stepId];
        assertDefined(step);

        const partialStep: Partial<Step> = {};
        partialStep[key] = value;

        updateStep({ ...step, ...partialStep });
    }

    function changeStepMapOver(stepId: number, mapOver: CollectionTypeDescriptor) {
        set(stepMapOver.value, stepId, mapOver);
    }

    function resetStepInputMapOver(stepId: number) {
        set(stepInputMapOver.value, stepId, {});
    }

    function changeStepInputMapOver(stepId: number, inputName: string, mapOver: CollectionTypeDescriptor) {
        if (stepInputMapOver.value[stepId]) {
            set(stepInputMapOver.value[stepId]!, inputName, mapOver);
        } else {
            set(stepInputMapOver.value, stepId, { [inputName]: mapOver });
        }
    }

    function addConnection(connection: Connection) {
        const inputStep = getStep.value(connection.input.stepId);

        assertDefined(
            inputStep,
            `Failed to add connection, because step with id ${connection.input.stepId} is undefined`,
        );

        const input = inputStep.inputs.find((input) => input.name === connection.input.name);
        const connectionLink: ConnectionOutputLink = {
            output_name: connection.output.name,
            id: connection.output.stepId,
        };

        if (input && "input_subworkflow_step_id" in input && input.input_subworkflow_step_id !== undefined) {
            connectionLink["input_subworkflow_step_id"] = input.input_subworkflow_step_id;
        }

        let connectionLinks: ConnectionOutputLink[] = [connectionLink];
        let inputConnection = inputStep.input_connections[connection.input.name];

        if (inputConnection) {
            if (!Array.isArray(inputConnection)) {
                inputConnection = [inputConnection];
            }
            inputConnection = inputConnection.filter(
                (connection) =>
                    !(connection.id === connectionLink.id && connection.output_name === connectionLink.output_name),
            );
            connectionLinks = [...connectionLinks, ...inputConnection];
        }

        const updatedStep = {
            ...inputStep,
            input_connections: {
                ...inputStep.input_connections,
                [connection.input.name]: connectionLinks.sort((a, b) =>
                    a.id === b.id ? a.output_name.localeCompare(b.output_name) : a.id - b.id,
                ),
            },
        };

        updateStep(updatedStep);
    }

    function removeConnection(connection: Connection) {
        const inputStep = getStep.value(connection.input.stepId);

        assertDefined(
            inputStep,
            `Failed to remove connection, because step with id ${connection.input.stepId} is undefined`,
        );

        const inputConnections = inputStep.input_connections[connection.input.name];
        const newInputConnections = { ...inputStep.input_connections };

        if (getStepExtraInputs.value(inputStep.id).find((input) => connection.input.name === input.name)) {
            newInputConnections[connection.input.name] = undefined;
        } else {
            if (Array.isArray(inputConnections)) {
                const filtered = inputConnections.filter(
                    (outputLink) =>
                        !(
                            outputLink.id === connection.output.stepId &&
                            outputLink.output_name === connection.output.name
                        ),
                );

                if (filtered.length === 0) {
                    delete newInputConnections[connection.input.name];
                } else {
                    newInputConnections[connection.input.name] = filtered;
                }
            } else {
                delete newInputConnections[connection.input.name];
            }
        }

        updateStep({ ...inputStep, input_connections: newInputConnections });
    }

    const { deleteStepPosition, deleteStepTerminals } = useWorkflowStateStore(workflowId);

    function removeStep(stepId: number) {
        connectionStore
            .getConnectionsForStep(stepId)
            .forEach((connection) => connectionStore.removeConnection(getConnectionId(connection)));

        del(steps.value, stepId.toString());
        del(stepExtraInputs.value, stepId);
        del(stateStore.multiSelectedSteps, stepId);
        del(stepMapOver.value, stepId.toString());

        deleteStepPosition(stepId);
        deleteStepTerminals(stepId);
    }

    return {
        steps,
        stepMapOver,
        stepInputMapOver,
        stepIndex,
        stepExtraInputs,
        $reset,
        getStep,
        getStepExtraInputs,
        getStepIndex,
        hasActiveOutputs,
        hasInputSteps,
        workflowOutputs,
        duplicateLabels,
        addStep,
        insertNewStep,
        updateStep,
        updateStepValue,
        changeStepMapOver,
        resetStepInputMapOver,
        changeStepInputMapOver,
        addConnection,
        removeConnection,
        removeStep,
    };
});

function makeConnection(inputId: number, inputName: string, outputId: number, outputName: string): Connection {
    return {
        input: {
            stepId: inputId,
            name: inputName,
            connectorType: "input",
        },
        output: {
            stepId: outputId,
            name: outputName,
            connectorType: "output",
        },
    };
}

/** Fields on a source step that determine the shape of a synthesized gate port. */
function gatePortSourceShapeChanged(previousStep: Step, updatedStep: Step): boolean {
    return (
        previousStep.outputs !== updatedStep.outputs ||
        previousStep.when !== updatedStep.when ||
        previousStep.post_job_actions !== updatedStep.post_job_actions
    );
}

/** True when any input connection on `step` comes from the named source step. */
function stepReadsSource(step: Step, sourceStepId: number): boolean {
    return Object.values(step.input_connections ?? {}).some((links) => {
        return normalizeConnectionOutputLinks(links).some((link) => link.id === sourceStepId);
    });
}

function stepToConnections(step: Step): Connection[] {
    const connections: Connection[] = [];

    if (step.input_connections) {
        Object.entries(step?.input_connections).forEach(([inputName, outputArray]) => {
            if (outputArray === undefined) {
                return;
            }
            normalizeConnectionOutputLinks(outputArray).forEach((output) => {
                const connection = makeConnection(step.id, inputName, output.id, output.output_name);
                const connectionInput = step.inputs.find((input) => input.name == inputName);
                if (connectionInput && "input_subworkflow_step_id" in connectionInput) {
                    connection.input.input_subworkflow_step_id = connectionInput.input_subworkflow_step_id;
                }
                connections.push(connection);
            });
        });
    }

    return connections;
}

function findStepExtraInputs(step: Step, steps: Steps): InputTerminalSource[] {
    const extraInputs: InputTerminalSource[] = [];
    if (step.when === undefined) {
        return extraInputs;
    }
    Object.keys(step.input_connections ?? {}).forEach((inputName) => {
        if (step.inputs.find((input) => input.name === inputName)) {
            return;
        }
        const inputPath = presenceGateInputPath(step, inputName);
        if (!inputPath || !expressionReferencesInput(step.when, inputPath)) {
            return;
        }
        extraInputs.push(gatePortTerminalSource(step, inputName, steps));
    });
    return extraInputs;
}

/**
 * True when a connection name can be spelled as a JavaScript path into `inputs`.
 *
 * A conditional maps segment for segment, while a repeat connection such as
 * `queries_0|input2` maps to `inputs.queries[0].input2`. Walk tool state so `_0`
 * can be distinguished from a literal property suffix and ambiguous names declined.
 */
export function presenceGateIsSpellable(step: Step, inputName: string): boolean {
    return presenceGateInputPath(step, inputName) !== null;
}

/** The actual `inputs` expression path for a connected input, when unambiguous. */
export function presenceGateInputPath(step: Step, inputName: string): InputPath | null {
    return resolveConnectionNameToInputPath(inputName, step.tool_state);
}

/**
 * Shape a synthesized gate port after whatever feeds it.
 *
 * A probe carries a value into the expression and nothing consumes it, so its terminal
 * has to accept what the source produces. Optionality matters as much as type: a probe
 * fed by an optional input is otherwise a required parameter terminal, and the editor
 * refuses the very connection the gate depends on.
 */
function gatePortTerminalSource(step: Step, inputName: string, steps: Steps): InputTerminalSource {
    if (inputName === BOOLEAN_GATE_INPUT_NAME) {
        // `when` is a convention with a fixed meaning: the gate's own boolean.
        return {
            name: inputName,
            label: inputName,
            multiple: false,
            optional: false,
            input_type: "parameter",
            type: "boolean",
            extensions: [],
        };
    }
    const links = step.input_connections[inputName];
    const link = normalizeConnectionOutputLinks(links)[0];
    const sourceStep = link ? steps[link.id.toString()] : undefined;
    const output = sourceStep?.outputs.find((candidate) => candidate.name === link?.output_name);
    const base = {
        name: inputName,
        label: inputName,
        multiple: Boolean(output && isParameterOutput(output) && output.multiple),
        optional: Boolean(output?.optional) || Boolean(sourceStep?.when),
    };
    if (!output || isParameterOutput(output)) {
        return {
            ...base,
            input_type: "parameter",
            type: output?.type ?? "boolean",
            extensions: [],
        };
    }
    if (isCollectionOutput(output)) {
        return {
            ...base,
            input_type: "dataset_collection",
            collection_types: output.collection_type ? [output.collection_type] : [],
            fields: [],
            column_definitions: null,
            extensions: effectiveOutputExtensions(sourceStep, output),
        };
    }
    return {
        ...base,
        input_type: "dataset",
        extensions: effectiveOutputExtensions(sourceStep, output),
    };
}

function effectiveOutputExtensions(sourceStep: Step | undefined, output: DataOutput | CollectionOutput): string[] {
    const changeDatatype = sourceStep?.post_job_actions?.[`ChangeDatatypeAction${output.name}`];
    if (changeDatatype) {
        const newtype = changeDatatype.action_arguments.newtype;
        return newtype ? [newtype] : [];
    }
    return output.extensions ?? [];
}

function isParameterOutput(output: OutputTerminalSource): output is ParameterOutput {
    return "parameter" in output && Boolean(output.parameter);
}

function isCollectionOutput(output: OutputTerminalSource): output is CollectionOutput {
    return "collection" in output && Boolean(output.collection);
}
