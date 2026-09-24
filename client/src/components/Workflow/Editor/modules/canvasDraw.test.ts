import { beforeEach, describe, expect, it, vi } from "vitest";

import type { GraphStep } from "@/composables/useInvocationGraph";
import type { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import type { Step } from "@/stores/workflowStepStore";

import { drawStepBorders, drawSteps, getStepColor, initStateColors } from "./canvasDraw";

/**
 * Makes a mock CSSStyleDeclaration whose `getPropertyValue` resolves CSS custom properties
 * from a plain object. Simulates how `initStateColors` reads `--state-color-*` vars from
 * a real element's computed style at mount time.
 */
function makeMockStyle(vars: Record<string, string>): CSSStyleDeclaration {
    return { getPropertyValue: (prop: string) => vars[prop] ?? "" } as unknown as CSSStyleDeclaration;
}

/** Makes a mock Step object provided with default values, allowing overrides. */
function makeStep(overrides: Partial<Step> = {}): Step {
    return { id: 0, position: { left: 10, top: 20 }, errors: null, type: "tool", ...overrides } as unknown as Step;
}

/** Makes a mock GraphStep object provided with default values, allowing overrides. */
function makeGraphStep(overrides: Partial<GraphStep> = {}): GraphStep {
    return makeStep(overrides as Partial<Step>) as unknown as GraphStep;
}

/**
 * Makes a mock CanvasRenderingContext2D with spied drawing methods. Simulates the canvas
 * context passed to `drawSteps`/`drawStepBorders` so tests can assert on draw calls
 * without needing a real DOM canvas element.
 */
function makeCtx(): CanvasRenderingContext2D {
    return {
        beginPath: vi.fn(),
        rect: vi.fn(),
        fill: vi.fn(),
        stroke: vi.fn(),
        fillStyle: "",
        strokeStyle: "",
        lineWidth: 0,
    } as unknown as CanvasRenderingContext2D;
}

/** Makes a mock workflow state store with specified step positions. */
function makeStateStore(
    positions: Record<number, { width: number; height: number }>,
): ReturnType<typeof useWorkflowStateStore> {
    return { stepPosition: positions } as unknown as ReturnType<typeof useWorkflowStateStore>;
}

const MOCK_COLORS: Record<string, string> = {
    "--state-color-ok": "#ok-color",
    "--state-color-error": "#error-color",
    "--state-color-uninitialized": "#uninitialized-color",
};

describe("initStateColors + getStepColor", () => {
    beforeEach(() => {
        initStateColors(makeMockStyle(MOCK_COLORS));
    });

    describe("plain editor steps (no headerClass)", () => {
        it("returns nodeColor when no errors", () => {
            expect(getStepColor(makeStep(), "#node", "#error")).toBe("#node");
        });

        it("returns errorColor when step has errors", () => {
            expect(getStepColor(makeStep({ errors: ["something went wrong"] }), "#node", "#error")).toBe("#error");
        });
    });

    describe("invocation steps (with headerClass)", () => {
        it("returns the CSS var color for an active header-* class", () => {
            const step = makeGraphStep({ headerClass: { "node-header-invocation": true, "header-ok": true } });
            expect(getStepColor(step, "#node", "#error")).toBe(MOCK_COLORS["--state-color-ok"]);
        });

        it("returns the CSS var color for header-error", () => {
            const step = makeGraphStep({
                headerClass: { "node-header-invocation": true, "header-error": true },
            });
            expect(getStepColor(step, "#node", "#error")).toBe(MOCK_COLORS["--state-color-error"]);
        });

        it("ignores inactive header-* classes and falls back to nodeColor", () => {
            const step = makeGraphStep({
                headerClass: { "node-header-invocation": true, "header-ok": false },
            });
            expect(getStepColor(step, "#node", "#error")).toBe("#node");
        });

        it("falls back to nodeColor when headerClass has no active header-* keys", () => {
            const step = makeGraphStep({ headerClass: { "node-header-invocation": true } });
            expect(getStepColor(step, "#node", "#error")).toBe("#node");
        });

        it("returns the CSS var color for header-uninitialized", () => {
            const step = makeGraphStep({
                headerClass: { "node-header-invocation": true, "header-uninitialized": true },
            });
            expect(getStepColor(step, "#node", "#error")).toBe(MOCK_COLORS["--state-color-uninitialized"]);
        });
    });
});

describe("drawSteps", () => {
    it("fills each step rect using the provided color", () => {
        const ctx = makeCtx();
        const steps = [makeStep({ id: 1, position: { left: 5, top: 10 } })];
        const stateStore = makeStateStore({ 1: { width: 100, height: 40 } });

        drawSteps(ctx, steps, "#ff0000", stateStore);

        expect(ctx.fillStyle).toBe("#ff0000");
        expect(ctx.beginPath).toHaveBeenCalled();
        expect(ctx.rect).toHaveBeenCalledWith(5, 10, 100, 40);
        expect(ctx.fill).toHaveBeenCalled();
    });

    it("skips steps with no recorded position", () => {
        const ctx = makeCtx();
        const steps = [makeStep({ id: 99 })];
        const stateStore = makeStateStore({});

        drawSteps(ctx, steps, "#ff0000", stateStore);

        expect(ctx.rect).not.toHaveBeenCalled();
    });
});

describe("drawStepBorders", () => {
    it("strokes each step rect using the provided border color", () => {
        const ctx = makeCtx();
        const steps = [makeStep({ id: 1, position: { left: 5, top: 10 } })];
        const stateStore = makeStateStore({ 1: { width: 100, height: 40 } });

        drawStepBorders(ctx, steps, "#0000ff", stateStore);

        expect(ctx.strokeStyle).toBe("#0000ff");
        expect(ctx.lineWidth).toBe(1);
        expect(ctx.rect).toHaveBeenCalledWith(5, 10, 100, 40);
        expect(ctx.stroke).toHaveBeenCalled();
    });

    it("skips steps with no recorded position", () => {
        const ctx = makeCtx();
        const steps = [makeStep({ id: 99 })];
        const stateStore = makeStateStore({});

        drawStepBorders(ctx, steps, "#0000ff", stateStore);

        expect(ctx.rect).not.toHaveBeenCalled();
    });
});
