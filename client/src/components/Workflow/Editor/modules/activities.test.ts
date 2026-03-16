import { createTestingPinia } from "@pinia/testing";
import { setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ref } from "vue";

import { useWorkflowActivities } from "./activities";

describe("useWorkflowActivities", () => {
    beforeEach(() => {
        const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
        setActivePinia(pinia);
    });

    it("excludes custom tools when canUseUnprivilegedTools is false", () => {
        const activities = useWorkflowActivities("workflow-editor", ref(false), ref(false), ref(0), ref(false));
        expect(activities.value.map((a) => a.id)).not.toContain("workflow-editor-user-defined-tools");
    });

    it("includes custom tools when canUseUnprivilegedTools is true", () => {
        const activities = useWorkflowActivities("workflow-editor", ref(false), ref(false), ref(0), ref(true));
        expect(activities.value.map((a) => a.id)).toContain("workflow-editor-user-defined-tools");
    });

    it("reflects undoStackLength reactively as the Changes activity indicator", () => {
        const undoStackLength = ref(5);
        const activities = useWorkflowActivities(
            "workflow-editor",
            ref(false),
            ref(false),
            undoStackLength,
            ref(false),
        );
        const changesActivity = () => activities.value.find((a) => a.id === "workflow-undo-redo");

        expect(changesActivity()?.indicator).toBe(5);
        undoStackLength.value = 10;
        expect(changesActivity()?.indicator).toBe(10);
    });

    it("reflects hasChanges reactively as the Save activity tooltip", () => {
        const hasChanges = ref(false);
        const activities = useWorkflowActivities("workflow-editor", ref(false), hasChanges, ref(0), ref(false));
        const saveTooltip = () => activities.value.find((a) => a.id === "save-workflow")?.tooltip;

        expect(saveTooltip()).toBe("No changes to save");
        hasChanges.value = true;
        expect(saveTooltip()).toBe("Save current changes");
    });
});
