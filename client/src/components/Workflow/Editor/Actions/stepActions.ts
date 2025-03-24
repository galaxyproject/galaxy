import { replaceLabel } from "@/components/Markdown/parse";
import { useToast } from "@/composables/toast";
import { useRefreshFromStore } from "@/stores/refreshFromStore";
import { LazyUndoRedoAction, UndoRedoAction, type UndoRedoStore } from "@/stores/undoRedoStore";
import { type WorkflowConnectionStore } from "@/stores/workflowConnectionStore";
import { useWorkflowCommentStore } from "@/stores/workflowEditorCommentStore";
import { type WorkflowStateStore } from "@/stores/workflowEditorStateStore";
import { type NewStep, type Step, useWorkflowStepStore, type WorkflowStepStore } from "@/stores/workflowStepStore";
import type { Connection } from "@/stores/workflowStoreTypes";
import { assertDefined } from "@/utils/assertions";

import { cloneStepWithUniqueLabel, getLabelSet } from "./cloneStep";

export class LazyMutateStepAction<K extends keyof Step> extends LazyUndoRedoAction {
    key: K;
    fromValue: Step[K];
    toValue: Step[K];
    stepId;
    stepStore;
    stepLabel;
    onUndoRedo?: () => void;

    get name() {
        return this.internalName ?? `modify step ${this.stepLabel}`;
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

        this.stepLabel = `${stepId + 1}`;
        const step = this.stepStore.getStep(stepId);

        if (step) {
            this.stepLabel = `"${stepId + 1}: ${step.label ?? step.name}"`;
        }
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

function onLabelSet(
    classInstance: LazySetLabelAction | LazySetOutputLabelAction,
    from: string | null | undefined,
    to: string | null | undefined
) {
    const markdown = classInstance.stateStore.report.markdown ?? "";
    const newMarkdown = replaceLabel(markdown, classInstance.labelType, from, to);

    if (markdown !== newMarkdown) {
        classInstance.stateStore.report.markdown = newMarkdown;
        classInstance.success(
            `${classInstance.labelTypeTitle} label updated from "${from}" to "${to}" in workflow report.`
        );
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

    run() {
        onLabelSet(this, this.fromValue, this.toValue);
    }

    undo() {
        super.undo();
        onLabelSet(this, this.toValue, this.fromValue);
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
    labelType = "output" as const;
    labelTypeTitle = "Output" as const;

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

    run() {
        onLabelSet(this, this.fromLabel, this.toLabel);
    }

    undo() {
        super.undo();
        onLabelSet(this, this.toLabel, this.fromLabel);
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
    stepLabel;
    onUndoRedo?: () => void;

    get name() {
        return this.internalName ?? `modify step ${this.stepLabel}`;
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

        this.stepLabel = `${stepId + 1}`;
        const step = this.stepStore.getStep(stepId);

        if (step) {
            this.stepLabel = `"${stepId + 1}: ${step.label ?? step.name}"`;
        }
    }

    isEmpty() {
        return Object.keys(this.fromPartial).length === 0;
    }

    run() {
        const step = this.stepStore.getStep(this.stepId);
        assertDefined(step);
        this.stepStore.updateStep({ ...step, ...this.toPartial });
    }

    undo() {
        const step = this.stepStore.getStep(this.stepId);
        assertDefined(step);
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
    }
}

export class RemoveStepAction extends UndoRedoAction {
    stepStore;
    stateStore;
    connectionStore;
    step: Step;
    connections: Connection[];

    constructor(
        stepStore: WorkflowStepStore,
        stateStore: WorkflowStateStore,
        connectionStore: WorkflowConnectionStore,
        step: Step
    ) {
        super();
        this.stepStore = stepStore;
        this.stateStore = stateStore;
        this.connectionStore = connectionStore;
        this.step = structuredClone(step);
        this.connections = structuredClone(this.connectionStore.getConnectionsForStep(this.step.id));
    }

    get name() {
        return `remove step "${this.step.id} ${this.step.label ?? this.step.name}"`;
    }

    run() {
        this.stepStore.removeStep(this.step.id);
        this.stateStore.activeNodeId = null;
        this.stateStore.hasChanges = true;
    }

    undo() {
        this.stepStore.addStep(structuredClone(this.step), false, false);
        this.connections.forEach((connection) => this.connectionStore.addConnection(connection));
        this.stateStore.hasChanges = true;
    }
}

export class CopyStepAction extends UndoRedoAction {
    stepStore;
    stateStore;
    step: NewStep;
    stepLabel;
    stepId?: number;
    onUndoRedo?: () => void;

    constructor(stepStore: WorkflowStepStore, stateStore: WorkflowStateStore, step: Step) {
        super();
        this.stepStore = stepStore;
        this.stateStore = stateStore;

        const labelSet = getLabelSet(stepStore);
        this.stepLabel = `${step.id + 1}: ${step.label ?? step.name}`;
        this.step = cloneStepWithUniqueLabel(step, labelSet);
        delete this.step.id;
    }

    get name() {
        return `duplicate step "${this.stepLabel}"`;
    }

    run() {
        const newStep = this.stepStore.addStep(structuredClone(this.step));
        this.stepId = newStep.id;
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
    stepLabel;

    constructor(stateStore: WorkflowStateStore, stepStore: WorkflowStepStore, stepId: number) {
        super();

        this.stateStore = stateStore;
        this.stepStore = stepStore;
        this.stepId = stepId;
        this.toggleTo = !this.stateStore.getStepMultiSelected(stepId);

        const label = this.stepStore.getStep(this.stepId)?.label;
        this.stepLabel = label ?? `${this.stepId + 1}`;
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

interface Positions {
    steps: { id: string; x: number; y: number }[];
    comments: { id: string; x: number; y: number; w: number; h: number }[];
}

export class AutoLayoutAction extends UndoRedoAction {
    stepStore;
    commentStore;
    positions: Positions;
    oldPositions: Positions;
    workflowId;
    ran;

    constructor(workflowId: string) {
        super();

        this.workflowId = workflowId;
        this.stepStore = useWorkflowStepStore(workflowId);
        this.commentStore = useWorkflowCommentStore(workflowId);

        this.positions = {
            steps: [],
            comments: [],
        };

        this.oldPositions = {
            steps: [],
            comments: [],
        };

        this.ran = false;
    }

    get name() {
        return "auto layout";
    }

    private mapPositionsToStore(positions: Positions) {
        positions.steps.map((p) => {
            const step = this.stepStore.steps[p.id];
            if (step) {
                this.stepStore.updateStep({
                    ...step,
                    position: {
                        top: p.y,
                        left: p.x,
                    },
                });
            }
        });

        positions.comments.map((c) => {
            const id = parseInt(c.id, 10);
            const comment = this.commentStore.commentsRecord[id];
            if (comment) {
                this.commentStore.changePosition(id, [c.x, c.y]);
                this.commentStore.changeSize(id, [c.w, c.h]);
            }
        });
    }

    async run() {
        this.ran = true;

        this.oldPositions.steps = Object.values(this.stepStore.steps).map((step) => ({
            id: `${step.id}`,
            x: step.position?.left ?? 0,
            y: step.position?.top ?? 0,
        }));

        this.oldPositions.comments = this.commentStore.comments.map((comment) => ({
            id: `${comment.id}`,
            x: comment.position[0],
            y: comment.position[1],
            w: comment.size[0],
            h: comment.size[1],
        }));

        const { autoLayout } = await import(
            /* webpackChunkName: "workflowLayout" */ "@/components/Workflow/Editor/modules/layout"
        );

        this.commentStore.resolveCommentsInFrames();
        this.commentStore.resolveStepsInFrames();

        const newPositions = await autoLayout(this.workflowId, this.stepStore.steps, this.commentStore.comments);

        assertDefined(newPositions);

        this.positions = newPositions as Positions;

        if (this.ran) {
            this.mapPositionsToStore(this.positions);
        }
    }

    undo() {
        this.ran = false;
        this.mapPositionsToStore(this.oldPositions);
    }

    redo() {
        this.mapPositionsToStore(this.positions);
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

            if (name) {
                actionForKey.name = name;
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
                stateStore.hasChanges = true;
            };

            return action;
        }
    }

    function setPosition(step: Step, position: NonNullable<Step["position"]>) {
        changeValueOrCreateAction({
            step,
            key: "position",
            value: position,
            name: `move step "${step.id + 1}: ${step.label ?? step.name}"`,
        });
    }

    function setAnnotation(step: Step, annotation: Step["annotation"]) {
        changeValueOrCreateAction({
            step,
            key: "annotation",
            value: annotation,
            name: `edit annotation of step "${step.id + 1}: ${step.label ?? step.name}"`,
        });
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
            name: `edit output label of step "${step.id + 1}: ${step.label ?? step.name}"`,
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
            name: `change label of step ${step.id + 1} to "${label}"`,
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
                stateStore.hasChanges = true;
                refresh();
            };
            undoRedoStore.applyAction(action);
        }
    }

    function removeStep(step: Step) {
        const action = new RemoveStepAction(stepStore, stateStore, connectionStore, step);
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
