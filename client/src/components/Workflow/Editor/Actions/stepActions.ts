import { UndoRedoAction, UndoRedoStore } from "@/stores/undoRedoStore";
import type { Step, WorkflowStepStore } from "@/stores/workflowStepStore";

class LazyMutateStepAction<K extends keyof Step> extends UndoRedoAction {
    key: K;
    fromValue: Step[K];
    toValue: Step[K];
    stepId;
    stepStore;

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
    }

    redo() {
        this.stepStore.updateStepValue(this.stepId, this.key, this.toValue);
    }
}

export function useStepActions(stepStore: WorkflowStepStore, undoRedoStore: UndoRedoStore) {
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

    return {
        setPosition,
        setAnnotation,
        setLabel,
    };
}
