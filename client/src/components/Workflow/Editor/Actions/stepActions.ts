import { useRefreshFromStore } from "@/stores/refreshFromStore";
import { UndoRedoAction, UndoRedoStore } from "@/stores/undoRedoStore";
import { WorkflowStateStore } from "@/stores/workflowEditorStateStore";
import type { Step, WorkflowStepStore } from "@/stores/workflowStepStore";
import { assertDefined } from "@/utils/assertions";

class LazyMutateStepAction<K extends keyof Step> extends UndoRedoAction {
    key: K;
    fromValue: Step[K];
    toValue: Step[K];
    stepId;
    stepStore;
    onUndoRedo?: () => void;

    constructor(stepStore: WorkflowStepStore, stepId: number, key: K, fromValue: Step[K], toValue: Step[K]) {
        super();
        this.stepStore = stepStore;
        this.stepId = stepId;
        this.key = key;
        this.fromValue = fromValue;
        this.toValue = toValue;

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

export class UpdateStepAction extends UndoRedoAction {
    stepStore;
    stateStore;
    stepId;
    fromPartial;
    toPartial;
    onUndoRedo?: () => void;

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
    showAttributesCallback;
    step: Step;

    constructor(
        stepStore: WorkflowStepStore,
        stateStore: WorkflowStateStore,
        showAttributesCallback: () => void,
        step: Step
    ) {
        super();
        this.stepStore = stepStore;
        this.stateStore = stateStore;
        this.showAttributesCallback = showAttributesCallback;
        this.step = structuredClone(step);
    }

    run() {
        this.stepStore.removeStep(this.step.id);
        this.showAttributesCallback();
    }

    undo() {
        this.stepStore.addStep(structuredClone(this.step));
        this.stateStore.activeNodeId = this.step.id;
    }
}

export function useStepActions(
    stepStore: WorkflowStepStore,
    undoRedoStore: UndoRedoStore,
    stateStore: WorkflowStateStore
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

    /**
     * Mutates a queued lazy action, if a matching one exists,
     * otherwise creates a new lazy action ans queues it.
     */
    function changeValueOrCreateAction<K extends keyof Step>(step: Step, key: K, value: Step[K]) {
        const actionForKey = actionForIdAndKey(step.id, key);

        if (actionForKey) {
            actionForKey.changeValue(value);
        } else {
            const action = new LazyMutateStepAction(stepStore, step.id, key, step[key], value);
            undoRedoStore.applyLazyAction(action);

            action.onUndoRedo = () => {
                stateStore.activeNodeId = step.id;
                stateStore.hasChanges = true;
            };
        }
    }

    function setPosition(step: Step, position: NonNullable<Step["position"]>) {
        changeValueOrCreateAction(step, "position", position);
    }

    function setAnnotation(step: Step, annotation: Step["annotation"]) {
        changeValueOrCreateAction(step, "annotation", annotation);
    }

    function setLabel(step: Step, label: Step["label"]) {
        changeValueOrCreateAction(step, "label", label);
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
        const action = new RemoveStepAction(stepStore, stateStore, showAttributesCallback, step);
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
        undoRedoStore.applyAction(action);
    }

    return {
        setPosition,
        setAnnotation,
        setLabel,
        setData,
        removeStep,
        updateStep,
    };
}
