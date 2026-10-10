import { beforeEach, describe, expect, it } from "vitest";
import { type Ref, ref, shallowRef } from "vue";

import { setupTestPinia } from "@/stores/testUtils";

import { useSpecialWorkflowActivities, useWorkflowActivities } from "./activities";
import type { LintData } from "./useLinting";

interface WorkflowActivityInputs {
    hasChanges?: Ref<boolean>;
    undoStackLength?: Ref<number>;
    canUseUnprivilegedTools?: Ref<boolean>;
}

function setUpWorkflowActivities({
    hasChanges = ref(false),
    undoStackLength = ref(0),
    canUseUnprivilegedTools = ref(false),
}: WorkflowActivityInputs = {}) {
    const activities = useWorkflowActivities(
        "workflow-editor",
        ref(false),
        hasChanges,
        undoStackLength,
        canUseUnprivilegedTools,
    );
    return {
        activityIds: () => activities.value.map((activity) => activity.id),
        findActivity: (id: string) => activities.value.find((activity) => activity.id === id),
    };
}

interface IssueCounts {
    totalPriority?: number;
    resolvedPriority?: number;
    totalAttribute?: number;
    resolvedAttribute?: number;
}

function bestPracticesActivityFor({
    totalPriority = 0,
    resolvedPriority = 0,
    totalAttribute = 0,
    resolvedAttribute = 0,
}: IssueCounts = {}) {
    const issueCounts: Pick<
        LintData,
        "totalPriorityIssues" | "resolvedPriorityIssues" | "totalAttributeIssues" | "resolvedAttributeIssues"
    > = {
        totalPriorityIssues: ref(totalPriority),
        resolvedPriorityIssues: ref(resolvedPriority),
        totalAttributeIssues: ref(totalAttribute),
        resolvedAttributeIssues: ref(resolvedAttribute),
    };
    const { bestPracticesActivity } = useSpecialWorkflowActivities(shallowRef({ lintData: issueCounts as LintData }));
    return bestPracticesActivity.value;
}

describe("useWorkflowActivities", () => {
    beforeEach(() => {
        setupTestPinia();
    });

    it("excludes custom tools when canUseUnprivilegedTools is false", () => {
        const { activityIds } = setUpWorkflowActivities({ canUseUnprivilegedTools: ref(false) });

        expect(activityIds()).not.toContain("workflow-editor-user-defined-tools");
    });

    it("includes custom tools when canUseUnprivilegedTools is true", () => {
        const { activityIds } = setUpWorkflowActivities({ canUseUnprivilegedTools: ref(true) });

        expect(activityIds()).toContain("workflow-editor-user-defined-tools");
    });

    it("reflects undoStackLength reactively as the Changes activity indicator", () => {
        const undoStackLength = ref(5);
        const { findActivity } = setUpWorkflowActivities({ undoStackLength });

        expect(findActivity("workflow-undo-redo")?.indicator).toBe(5);
        undoStackLength.value = 10;
        expect(findActivity("workflow-undo-redo")?.indicator).toBe(10);
    });

    it("reflects hasChanges reactively as the Save activity tooltip", () => {
        const hasChanges = ref(false);
        const { findActivity } = setUpWorkflowActivities({ hasChanges });

        expect(findActivity("save-workflow")?.tooltip).toBe("No changes to save");
        hasChanges.value = true;
        expect(findActivity("save-workflow")?.tooltip).toBe("Save current changes");
    });
});

describe("useSpecialWorkflowActivities", () => {
    describe("Best Practices indicator", () => {
        it("is undefined when there are no issues", () => {
            expect(bestPracticesActivityFor().indicator).toBeUndefined();
        });

        it("shows remaining critical count when priority issues are unresolved", () => {
            expect(bestPracticesActivityFor({ totalPriority: 3, resolvedPriority: 1 }).indicator).toBe(2);
        });

        it("shows true when only minor issues remain", () => {
            expect(bestPracticesActivityFor({ totalAttribute: 2 }).indicator).toBe(true);
        });

        it("uses danger variant for a numeric indicator", () => {
            expect(bestPracticesActivityFor({ totalPriority: 1 }).indicatorVariant).toBe("danger");
        });

        it("uses primary variant for an icon indicator", () => {
            expect(bestPracticesActivityFor({ totalAttribute: 1 }).indicatorVariant).toBe("primary");
        });
    });

    describe("Best Practices tooltip", () => {
        it("shows default tooltip when no issues remain", () => {
            expect(bestPracticesActivityFor().tooltip).toBe("Test workflow for best practices");
        });

        it("uses singular wording for exactly 1 critical issue", () => {
            expect(bestPracticesActivityFor({ totalPriority: 1 }).tooltip).toBe(
                "1 critical best practice issue remains",
            );
        });

        it("uses plural wording for multiple critical issues", () => {
            expect(bestPracticesActivityFor({ totalPriority: 3, resolvedPriority: 1 }).tooltip).toBe(
                "2 critical best practice issues remain",
            );
        });

        it("shows minor issue count when only minor issues remain", () => {
            expect(bestPracticesActivityFor({ totalAttribute: 2, resolvedAttribute: 1 }).tooltip).toBe(
                "1 minor best practice issue remains",
            );
        });
    });
});
