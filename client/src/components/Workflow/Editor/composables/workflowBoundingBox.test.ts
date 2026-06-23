import { createTestingPinia } from "@pinia/testing";
import { setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import { type Step, useWorkflowStepStore } from "@/stores/workflowStepStore";

import { createMockStepPosition } from "../test_fixtures";
import { useWorkflowBoundingBox } from "./workflowBoundingBox";

const WORKFLOW_ID = "test-workflow";

describe("useWorkflowBoundingBox coordinate shift adjustment", () => {
    let stepStore: ReturnType<typeof useWorkflowStepStore>;
    let stateStore: ReturnType<typeof useWorkflowStateStore>;

    beforeEach(() => {
        const pinia = createTestingPinia({ createSpy: vi.fn, stubActions: false });
        setActivePinia(pinia);
        stepStore = useWorkflowStepStore(WORKFLOW_ID);
        stateStore = useWorkflowStateStore(WORKFLOW_ID);
    });

    /**
     * Helper to add a step to the store with position and dimensions.
     */
    function addStep(id: number, left: number, top: number, width: number, height: number) {
        stepStore.addStep({
            id,
            type: "tool",
            name: `Step ${id}`,
            tool_id: `tool_${id}`,
            position: { left, top },
            inputs: [],
            outputs: [],
            input_connections: {},
            workflow_outputs: [],
            post_job_actions: {},
            config_form: {},
            when: null,
        } as unknown as Step);
        // Set the step dimensions in stateStore (normally set by DOM measurements)
        stateStore.stepPosition[id] = createMockStepPosition(width, height);
    }

    describe("captureTransformAndBounds", () => {
        it("captures the current transform and bounding box bounds", () => {
            // Setup: Add a step at position (100, 50) with size 200x100
            addStep(1, 100, 50, 200, 100);

            const { captureTransformAndBounds } = useWorkflowBoundingBox(WORKFLOW_ID);

            const currentTransform = { x: -50, y: -25, k: 1.5 };
            const captured = captureTransformAndBounds(currentTransform);

            // Transform should be captured as-is
            expect(captured.transform).toEqual({ x: -50, y: -25, k: 1.5 });

            // Bounds should reflect the step's position (minX=100, minY=50)
            expect(captured.bounds.minX).toBe(100);
            expect(captured.bounds.minY).toBe(50);
        });

        it("captures bounds from multiple steps", () => {
            // Setup: Add steps at different positions
            addStep(1, 100, 50, 200, 100);
            addStep(2, 50, 200, 150, 80); // This one has smaller left (50)
            addStep(3, 300, 20, 100, 60); // This one has smaller top (20)

            const { captureTransformAndBounds } = useWorkflowBoundingBox(WORKFLOW_ID);

            const captured = captureTransformAndBounds({ x: 0, y: 0, k: 1 });

            // Bounds should be the minimum of all steps
            expect(captured.bounds.minX).toBe(50); // from step 2
            expect(captured.bounds.minY).toBe(20); // from step 3
        });
    });

    describe("calculateAdjustedTransform", () => {
        it("returns same transform when bounding box hasn't shifted", () => {
            // Setup: Add a step
            addStep(1, 100, 50, 200, 100);

            const { captureTransformAndBounds, calculateAdjustedTransform } = useWorkflowBoundingBox(WORKFLOW_ID);

            // Capture before (simulating before reload)
            const transformBefore = { x: -50, y: -25, k: 1 };
            const { bounds: boundsBefore } = captureTransformAndBounds(transformBefore);

            // No change to workflow positions (same bounding box)
            const adjustedTransform = calculateAdjustedTransform(transformBefore, boundsBefore);

            // Transform should be unchanged
            expect(adjustedTransform).toEqual({ x: -50, y: -25, k: 1 });
        });

        it("adjusts transform when backend shifts coordinates to the right (normalizes negative positions)", () => {
            // Scenario: Backend refactor creates a new input at negative position,
            // then normalizes all positions by shifting everything right.

            // Setup: Original workflow has a step at position (100, 50)
            addStep(1, 100, 50, 200, 100);

            const { captureTransformAndBounds, calculateAdjustedTransform } = useWorkflowBoundingBox(WORKFLOW_ID);

            // Capture state BEFORE refactor
            const transformBefore = { x: -50, y: -25, k: 1 };
            const { bounds: boundsBefore } = captureTransformAndBounds(transformBefore);

            // Simulate backend normalization by resetting and adding new workflow state:
            // Backend created new input at left=-120, then normalized all positions.
            // min_left becomes -120, so everything shifts right by 120.
            // Original step: 100 - (-120) = 220
            // New input: -120 - (-120) = 0
            stepStore.$reset();
            stateStore.$reset();
            addStep(1, 220, 50, 200, 100); // Original step shifted right
            addStep(2, 0, 0, 150, 80); // New input at normalized position (0, 0)

            // Calculate adjusted transform
            const adjustedTransform = calculateAdjustedTransform(transformBefore, boundsBefore);

            // The bounding box shifted: old minX=100, new minX=0; old minY=50, new minY=0
            // offsetX = 100 - 0 = 100, offsetY = 50 - 0 = 50
            // adjustedX = -50 + (100 * 1) = 50
            // adjustedY = -25 + (50 * 1) = 25
            expect(adjustedTransform.x).toBe(50);
            expect(adjustedTransform.y).toBe(25);
            expect(adjustedTransform.k).toBe(1);
        });

        it("adjusts transform correctly with zoom factor", () => {
            // Setup: Original workflow
            addStep(1, 100, 50, 200, 100);

            const { captureTransformAndBounds, calculateAdjustedTransform } = useWorkflowBoundingBox(WORKFLOW_ID);

            // Capture state BEFORE at 2x zoom
            const transformBefore = { x: -100, y: -50, k: 2 };
            const { bounds: boundsBefore } = captureTransformAndBounds(transformBefore);

            // Simulate backend normalization by resetting and adding new state
            stepStore.$reset();
            stateStore.$reset();
            addStep(1, 220, 50, 200, 100);
            addStep(2, 0, 0, 150, 80);

            const adjustedTransform = calculateAdjustedTransform(transformBefore, boundsBefore);

            // offsetX = 100 - 0 = 100, offsetY = 50 - 0 = 50
            // scaledOffsetX = 100 * 2 = 200, scaledOffsetY = 50 * 2 = 100
            // adjustedX = -100 + 200 = 100
            // adjustedY = -50 + 100 = 50
            expect(adjustedTransform.x).toBe(100);
            expect(adjustedTransform.y).toBe(50);
            expect(adjustedTransform.k).toBe(2);
        });

        it("adjusts transform when coordinates shift in both X and Y", () => {
            // Setup: Original workflow
            addStep(1, 100, 80, 200, 100);

            const { captureTransformAndBounds, calculateAdjustedTransform } = useWorkflowBoundingBox(WORKFLOW_ID);

            // Capture state BEFORE
            const transformBefore = { x: -50, y: -40, k: 1 };
            const { bounds: boundsBefore } = captureTransformAndBounds(transformBefore);

            // Simulate backend normalization that shifts both X and Y
            // New min becomes (0, 0), original step was at (100, 80)
            stepStore.$reset();
            stateStore.$reset();
            addStep(1, 220, 90, 200, 100); // Shifted
            addStep(2, 0, 0, 150, 80); // New input normalized to (0, 0)

            const adjustedTransform = calculateAdjustedTransform(transformBefore, boundsBefore);

            // offsetX = 100 - 0 = 100, offsetY = 80 - 0 = 80
            // adjustedX = -50 + 100 = 50
            // adjustedY = -40 + 80 = 40
            expect(adjustedTransform.x).toBe(50);
            expect(adjustedTransform.y).toBe(40);
            expect(adjustedTransform.k).toBe(1);
        });

        it("handles workflow being shifted to more negative positions", () => {
            // Edge case: What if the new bounding box has larger minX/minY?
            // This could happen if steps are removed or positions change differently.

            // Setup: Original workflow with step at (50, 30)
            addStep(1, 50, 30, 200, 100);

            const { captureTransformAndBounds, calculateAdjustedTransform } = useWorkflowBoundingBox(WORKFLOW_ID);

            // Capture state BEFORE
            const transformBefore = { x: -25, y: -15, k: 1 };
            const { bounds: boundsBefore } = captureTransformAndBounds(transformBefore);

            // Simulate step being moved/normalized to a larger position
            stepStore.$reset();
            stateStore.$reset();
            addStep(1, 100, 80, 200, 100);

            const adjustedTransform = calculateAdjustedTransform(transformBefore, boundsBefore);

            // offsetX = 50 - 100 = -50 (negative offset, shift left)
            // adjustedX = -25 + (-50) = -75
            // offsetY = 30 - 80 = -50
            // adjustedY = -15 + (-50) = -65
            expect(adjustedTransform.x).toBe(-75);
            expect(adjustedTransform.y).toBe(-65);
            expect(adjustedTransform.k).toBe(1);
        });

        it("returns original transform when workflow has no steps (empty bounding box)", () => {
            // Edge case: Switching to a workflow version with 0 steps
            // The bounding box will have Infinity values, which would cause NaN

            // Setup: Original workflow with a step
            addStep(1, 100, 50, 200, 100);

            const { captureTransformAndBounds, calculateAdjustedTransform } = useWorkflowBoundingBox(WORKFLOW_ID);

            // Capture state BEFORE
            const transformBefore = { x: -50, y: -25, k: 1.5 };
            const { bounds: boundsBefore } = captureTransformAndBounds(transformBefore);

            // Simulate switching to empty workflow version
            stepStore.$reset();
            stateStore.$reset();
            // No steps added - empty workflow

            const adjustedTransform = calculateAdjustedTransform(transformBefore, boundsBefore);

            // Should return original transform unchanged (no NaN)
            expect(adjustedTransform.x).toBe(-50);
            expect(adjustedTransform.y).toBe(-25);
            expect(adjustedTransform.k).toBe(1.5);
            expect(Number.isFinite(adjustedTransform.x)).toBe(true);
            expect(Number.isFinite(adjustedTransform.y)).toBe(true);
        });

        it("returns original transform when starting from empty workflow", () => {
            // Edge case: Starting with empty workflow, then loading one with steps

            const { captureTransformAndBounds, calculateAdjustedTransform } = useWorkflowBoundingBox(WORKFLOW_ID);

            // Capture state BEFORE with empty workflow (bounds will be Infinity)
            const transformBefore = { x: 0, y: 0, k: 1 };
            const { bounds: boundsBefore } = captureTransformAndBounds(transformBefore);

            // Now add steps (simulating loading a workflow with steps)
            addStep(1, 100, 50, 200, 100);

            const adjustedTransform = calculateAdjustedTransform(transformBefore, boundsBefore);

            // Should return original transform unchanged (no NaN)
            expect(adjustedTransform.x).toBe(0);
            expect(adjustedTransform.y).toBe(0);
            expect(adjustedTransform.k).toBe(1);
            expect(Number.isFinite(adjustedTransform.x)).toBe(true);
            expect(Number.isFinite(adjustedTransform.y)).toBe(true);
        });
    });
});
