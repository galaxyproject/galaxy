import { replaceLabel } from "@/components/Markdown/parse";
import { useToast } from "@/composables/toast";
import { useRefreshFromStore } from "@/stores/refreshFromStore";
import { LazyUndoRedoAction, UndoRedoAction, UndoRedoStore } from "@/stores/undoRedoStore";
import { Connection, WorkflowConnectionStore } from "@/stores/workflowConnectionStore";
import { WorkflowStateStore } from "@/stores/workflowEditorStateStore";
import type { NewStep, Step, WorkflowStepStore } from "@/stores/workflowStepStore";
import { assertDefined } from "@/utils/assertions";

import { cloneStepWithUniqueLabel, getLabelSet } from "./cloneStep";

export class LazyMutateStepAction<K extends keyof Step> extends LazyUndoRedoAction {
    key: K;
    fromValue: Step[K];
    toValue: Step[K];
    stepId;
    stepStore;
    onUndoRedo?: () => void;

    get name() {
        return this.internalName ?? "modify step";
    }

    set name(name: string | undefined) {
        this.internalName = name;
    }

    constructor(stepStore: WorkflowStepStore, stepId: number, key: K, fromValue: Step[K], toValue: Step[K]) {
        super();
        this.stepStore = stepStore;
        this.stepId = stepId;
        this.key = key;
        this.fromValue = fromValue;
        this.toValue = toValue;
    }

    queued() {
        this.stepStore.updateStepValue(this.stepId, this.key, this.toValue);
    }

    changeValue(value: Step[K]) {
        this.toValue = value;
        this.stepStore.updateStepValue(this.stepId, this.key, this.toValue);
    }

    undo() {
        this.stepStore.updateStepValue(this.stepId, this.key, this.fromValue);
        this.onUndoRedo?.();
    }

    redo() {
        this.stepStore.updateStepValue(this.stepId, this.key, this.toValue);
        this.onUndoRedo?.();
    }
}

export class LazySetLabelAction extends LazyMutateStepAction<"label"> {
    labelType: "input" | "step";
    labelTypeTitle: "Input" | "Step";
    stateStore: WorkflowStateStore;
    success;

    constructor(
        stepStore: WorkflowStepStore,
        stateStore: WorkflowStateStore,
        stepId: number,
        fromValue: Step["label"],
        toValue: Step["label"]
    ) {
        super(stepStore, stepId, "label", fromValue, toValue);

        const step = this.stepStore.getStep(this.stepId);
        assertDefined(step);

        const stepType = step.type;
        const isInput = ["data_input", "data_collection_input", "parameter_input"].indexOf(stepType) >= 0;
        this.labelType = isInput ? "input" : "step";
        this.labelTypeTitle = isInput ? "Input" : "Step";
        this.stateStore = stateStore;
        this.success = useToast().success;
    }

    private toast(from: string, to: string) {
        this.success(`${this.labelTypeTitle} label updated from "${from}" to "${to}" in workflow report.`);
    }

    run() {
        const markdown = this.stateStore.report.markdown ?? "";
        const newMarkdown = replaceLabel(markdown, this.labelType, this.fromValue as string, this.toValue as string);
        this.stateStore.report.markdown = newMarkdown;
        this.toast(this.fromValue ?? "", this.toValue ?? "");
    }

    undo() {
        super.undo();

        const markdown = this.stateStore.report.markdown ?? "";
        const newMarkdown = replaceLabel(markdown, this.labelType, this.toValue as string, this.fromValue as string);
        this.stateStore.report.markdown = newMarkdown;
        this.toast(this.toValue ?? "", this.fromValue ?? "");
    }

    redo() {
        super.redo();
        this.run();
    }
}

export class LazySetOutputLabelAction extends LazyMutateStepAction<"workflow_outputs"> {
    success;
    fromLabel;
    toLabel;
    stateStore;

    constructor(
        stepStore: WorkflowStepStore,
        stateStore: WorkflowStateStore,
        stepId: number,
        fromValue: string | null,
        toValue: string | null,
        toOutputs: Step["workflow_outputs"]
    ) {
        const step = stepStore.getStep(stepId);
        assertDefined(step);
        const fromOutputs = structuredClone(step.workflow_outputs);

        super(stepStore, stepId, "workflow_outputs", fromOutputs, structuredClone(toOutputs));

        this.fromLabel = fromValue;
        this.toLabel = toValue;
        this.stateStore = stateStore;
        this.success = useToast().success;
    }

    private toast(from: string, to: string) {
        this.success(`Output label updated from "${from}" to "${to}" in workflow report.`);
    }

    run() {
        const markdown = this.stateStore.report.markdown ?? "";
        const newMarkdown = replaceLabel(markdown, "output", this.fromLabel, this.toLabel);
        this.stateStore.report.markdown = newMarkdown;
        this.toast(this.fromLabel ?? "", this.toLabel ?? "");
    }

    undo() {
        super.undo();

        const markdown = this.stateStore.report.markdown ?? "";
        const newMarkdown = replaceLabel(markdown, "output", this.toLabel, this.fromLabel);
        this.stateStore.report.markdown = newMarkdown;

        this.toast(this.toLabel ?? "", this.fromLabel ?? "");
    }

    redo() {
        this.run();
        super.redo();
    }
}

export class UpdateStepAction extends UndoRedoAction {
    stepStore;
    stateStore;
    stepId;
    fromPartial;
    toPartial;
    onUndoRedo?: () => void;

    get name() {
        return this.internalName ?? "modify step";
    }

    set name(name: string | undefined) {
        this.internalName = name;
    }

    constructor(
        stepStore: WorkflowStepStore,
        stateStore: WorkflowStateStore,
        stepId: number,
        fromPartial: Partial<Step>,
        toPartial: Partial<Step>
    ) {
        super();
        this.stepStore = stepStore;
        this.stateStore = stateStore;
        this.stepId = stepId;
        this.fromPartial = fromPartial;
        this.toPartial = toPartial;
    }

    isEmpty() {
        return Object.keys(this.fromPartial).length === 0;
    }

    run() {
        const step = this.stepStore.getStep(this.stepId);
        assertDefined(step);
        this.stateStore.activeNodeId = this.stepId;
        this.stepStore.updateStep({ ...step, ...this.toPartial });
    }

    undo() {
        const step = this.stepStore.getStep(this.stepId);
        assertDefined(step);
        this.stateStore.activeNodeId = this.stepId;
        this.stepStore.updateStep({ ...step, ...this.fromPartial });
        this.onUndoRedo?.();
    }

    redo() {
        this.run();
        this.onUndoRedo?.();
    }
}

export class SetDataAction extends UpdateStepAction {
    constructor(stepStore: WorkflowStepStore, stateStore: WorkflowStateStore, from: Step, to: Step) {
        const fromPartial: Partial<Step> = {};
        const toPartial: Partial<Step> = {};

        Object.entries(from).forEach(([key, value]) => {
            const otherValue = to[key as keyof Step] as any;

            if (JSON.stringify(value) !== JSON.stringify(otherValue)) {
                fromPartial[key as keyof Step] = structuredClone(value);
                toPartial[key as keyof Step] = structuredClone(otherValue);
            }
        });

        super(stepStore, stateStore, from.id, fromPartial, toPartial);
    }
}

export type InsertStepData = {
    contentId: Parameters<WorkflowStepStore["insertNewStep"]>[0];
    name: Parameters<WorkflowStepStore["insertNewStep"]>[1];
    type: Parameters<WorkflowStepStore["insertNewStep"]>[2];
    position: Parameters<WorkflowStepStore["insertNewStep"]>[3];
};

export class InsertStepAction extends UndoRedoAction {
    stepStore;
    stateStore;
    stepData;
    updateStepData?: Step;
    stepId?: number;
    newStepData?: Step;

    constructor(stepStore: WorkflowStepStore, stateStore: WorkflowStateStore, stepData: InsertStepData) {
        super();
        this.stepStore = stepStore;
        this.stateStore = stateStore;
        this.stepData = stepData;
    }

    get name() {
        return `insert ${this.stepData.name}`;
    }

    stepDataToTuple() {
        return Object.values(this.stepData) as Parameters<WorkflowStepStore["insertNewStep"]>;
    }

    getNewStepData() {
        assertDefined(this.newStepData);
        return this.newStepData;
    }

    run() {
        this.newStepData = this.stepStore.insertNewStep(...this.stepDataToTuple());
        this.stepId = this.newStepData.id;

        if (this.updateStepData) {
            this.stepStore.updateStep(this.updateStepData);
            this.stepId = this.updateStepData.id;
        }
    }

    undo() {
        assertDefined(this.stepId);
        this.stepStore.removeStep(this.stepId);
    }

    redo() {
        this.run();
        assertDefined(this.stepId);
        this.stateStore.activeNodeId = this.stepId;
    }
}

export class RemoveStepAction extends UndoRedoAction {
    stepStore;
    stateStore;
    connectionStore;
    showAttributesCallback;
    step: Step;
    connections: Connection[];

    constructor(
        stepStore: WorkflowStepStore,
        stateStore: WorkflowStateStore,
        connectionStore: WorkflowConnectionStore,
        showAttributesCallback: () => void,
        step: Step
    ) {
        super();
        this.stepStore = stepStore;
        this.stateStore = stateStore;
        this.connectionStore = connectionStore;
        this.showAttributesCallback = showAttributesCallback;
        this.step = structuredClone(step);
        this.connections = structuredClone(this.connectionStore.getConnectionsForStep(this.step.id));
    }

    get name() {
        return `remove ${this.step.label ?? this.step.name}`;
    }

    run() {
        this.stepStore.removeStep(this.step.id);
        this.showAttributesCallback();
        this.stateStore.hasChanges = true;
    }

    undo() {
        this.stepStore.addStep(structuredClone(this.step), false, false);
        this.connections.forEach((connection) => this.connectionStore.addConnection(connection));
        this.stateStore.activeNodeId = this.step.id;
        this.stateStore.hasChanges = true;
    }
}

export class CopyStepAction extends UndoRedoAction {
    stepStore;
    stateStore;
    step: NewStep;
    stepId?: number;
    onUndoRedo?: () => void;

    constructor(stepStore: WorkflowStepStore, stateStore: WorkflowStateStore, step: Step) {
        super();
        this.stepStore = stepStore;
        this.stateStore = stateStore;

        const labelSet = getLabelSet(stepStore);
        this.step = cloneStepWithUniqueLabel(step, labelSet);
        delete this.step.id;
    }

    get name() {
        return `duplicate step ${this.step.label ?? this.step.name}`;
    }

    run() {
        const newStep = this.stepStore.addStep(structuredClone(this.step));
        this.stepId = newStep.id;
        this.stateStore.activeNodeId = this.stepId;
        this.stateStore.hasChanges = true;
    }

    undo() {
        assertDefined(this.stepId);
        this.stepStore.removeStep(this.stepId);
    }
}

export class ToggleStepSelectedAction extends UndoRedoAction {
    stateStore;
    stepStore;
    stepId;
    toggleTo: boolean;

    constructor(stateStore: WorkflowStateStore, stepStore: WorkflowStepStore, stepId: number) {
        super();

        this.stateStore = stateStore;
        this.stepStore = stepStore;
        this.stepId = stepId;
        this.toggleTo = !this.stateStore.getStepMultiSelected(stepId);
    }

    get stepLabel() {
        const label = this.stepStore.getStep(this.stepId)?.label;
        return label ?? `${this.stepId + 1}`;
    }

    get name() {
        if (this.toggleTo === true) {
            return `add step ${this.stepLabel} to selection`;
        } else {
            return `remove step ${this.stepLabel} from selection`;
        }
    }

    run() {
        this.stateStore.setStepMultiSelected(this.stepId, this.toggleTo);
    }

    undo() {
        this.stateStore.setStepMultiSelected(this.stepId, !this.toggleTo);
    }
}

export function useStepActions(
    stepStore: WorkflowStepStore,
    undoRedoStore: UndoRedoStore,
    stateStore: WorkflowStateStore,
    connectionStore: WorkflowConnectionStore
) {
    /**
     * If the pending action is a `LazyMutateStepAction` and matches the step id and field key, returns it.
     * Otherwise returns `null`
     */
    function actionForIdAndKey(id: number, key: keyof Step) {
        const pendingAction = undoRedoStore.pendingLazyAction;

        if (pendingAction instanceof LazyMutateStepAction && pendingAction.stepId === id && pendingAction.key === key) {
            return pendingAction;
        } else {
            return null;
        }
    }

    interface ChangeValueOrCreateActionOptions<K extends keyof Step> {
        step: Step;
        key: K;
        value: Step[K];
        name?: string;
        actionConstructor?: () => LazyMutateStepAction<K>;
        keepActionAlive?: boolean;
        timeout?: number;
    }

    /**
     * Mutates a queued lazy action, if a matching one exists,
     * otherwise creates a new lazy action ans queues it.
     */
    function changeValueOrCreateAction<K extends keyof Step>(
        options: ChangeValueOrCreateActionOptions<K>
    ): InstanceType<typeof LazyMutateStepAction<K>> {
        const { step, key, value, name, keepActionAlive, timeout } = options;
        const actionForKey = actionForIdAndKey(step.id, key);

        if (actionForKey) {
            actionForKey.changeValue(value);

            if (keepActionAlive) {
                undoRedoStore.setLazyActionTimeout(timeout);
            }

            return actionForKey;
        } else {
            const actionConstructor =
                options.actionConstructor ??
                (() => new LazyMutateStepAction(stepStore, step.id, key, step[key], value));

            const action = actionConstructor();

            if (name) {
                action.name = name;
            }

            undoRedoStore.applyLazyAction(action, timeout);

            action.onUndoRedo = () => {
                stateStore.activeNodeId = step.id;
                stateStore.hasChanges = true;
            };

            return action;
        }
    }

    function setPosition(step: Step, position: NonNullable<Step["position"]>) {
        changeValueOrCreateAction({ step, key: "position", value: position, name: "change step position" });
    }

    function setAnnotation(step: Step, annotation: Step["annotation"]) {
        changeValueOrCreateAction({ step, key: "annotation", value: annotation, name: "modify step annotation" });
    }

    function setOutputLabel(
        step: Step,
        workflowOutputs: Step["workflow_outputs"],
        fromLabel: string | null,
        toLabel: string | null
    ) {
        const actionConstructor = () =>
            new LazySetOutputLabelAction(stepStore, stateStore, step.id, fromLabel, toLabel, workflowOutputs);

        changeValueOrCreateAction({
            step,
            key: "workflow_outputs",
            value: workflowOutputs,
            name: "modify step output label",
            actionConstructor,
            keepActionAlive: true,
            timeout: 2000,
        });
    }

    function setLabel(step: Step, label: Step["label"]) {
        const actionConstructor = () => new LazySetLabelAction(stepStore, stateStore, step.id, step.label, label);
        changeValueOrCreateAction({
            step,
            key: "label",
            value: label,
            name: "modify step label",
            actionConstructor,
            keepActionAlive: true,
            timeout: 2000,
        });
    }

    const { refresh } = useRefreshFromStore();

    function setData(from: Step, to: Step) {
        const action = new SetDataAction(stepStore, stateStore, from, to);

        if (!action.isEmpty()) {
            action.onUndoRedo = () => {
                stateStore.activeNodeId = from.id;
                stateStore.hasChanges = true;
                refresh();
            };
            undoRedoStore.applyAction(action);
        }
    }

    function removeStep(step: Step, showAttributesCallback: () => void) {
        const action = new RemoveStepAction(stepStore, stateStore, connectionStore, showAttributesCallback, step);
        undoRedoStore.applyAction(action);
    }

    function updateStep(id: number, toPartial: Partial<Step>) {
        const fromStep = stepStore.getStep(id);
        assertDefined(fromStep);
        const fromPartial: Partial<Step> = {};

        Object.keys(toPartial).forEach((key) => {
            fromPartial[key as keyof Step] = structuredClone(fromStep[key as keyof Step]) as any;
        });

        const action = new UpdateStepAction(stepStore, stateStore, id, fromPartial, toPartial);

        if (!action.isEmpty()) {
            action.onUndoRedo = () => {
                stateStore.activeNodeId = id;
                stateStore.hasChanges = true;
                refresh();
            };
            undoRedoStore.applyAction(action);
        }
    }

    function copyStep(step: Step) {
        const action = new CopyStepAction(stepStore, stateStore, step);
        undoRedoStore.applyAction(action);
    }

    return {
        setPosition,
        setAnnotation,
        setLabel,
        setData,
        setOutputLabel,
        removeStep,
        updateStep,
        copyStep,
    };
}
