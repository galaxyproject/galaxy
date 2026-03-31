import { beforeEach, describe, expect, it, vi } from "vitest";

import type { GraphStep } from "@/composables/useInvocationGraph";
import type { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import type { Step } from "@/stores/workflowStepStore";

import { drawStepBorders, drawSteps, getStepColor, initStateColors } from "./canvasDraw";

function makeMockStyle(vars: Record<string, string>): CSSStyleDeclaration {
    return { getPropertyValue: (prop: string) => vars[prop] ?? "" } as unknown as CSSStyleDeclaration;
}

function makeStep(overrides: Partial<Step> = {}): Step {
    return { id: 0, position: { left: 10, top: 20 }, errors: null, type: "tool", ...overrides } as unknown as Step;
}

function makeGraphStep(overrides: Partial<GraphStep> = {}): Step {
    return makeStep(overrides as Partial<Step>);
}

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

function makeStateStore(
    positions: Record<number, { width: number; height: number }>,
): ReturnType<typeof useWorkflowStateStore> {
    return { stepPosition: positions } as unknown as ReturnType<typeof useWorkflowStateStore>;
}

const STATE_COLORS = {
    "--state-color-ok": "#d4edda",
    "--state-color-error": "#f8d7da",
    "--state-color-running": "#fff3cd",
    "--state-color-new": "#e2e3e5",
    "--state-color-waiting": "#e2e3e5",
    "--state-color-queued": "#e2e3e5",
    "--state-color-undefined": "#e9ecef",
};

describe("initStateColors + getStepColor", () => {
    beforeEach(() => {
        initStateColors(makeMockStyle(STATE_COLORS));
    });

    describe("plain editor steps (no headerClass)", () => {
        it("returns nodeColor when no errors", () => {
            expect(getStepColor(makeStep(), "#node", "#error")).toBe("#node");
        });

        it("returns errorColor when step has errors", () => {
            expect(getStepColor(makeStep({ errors: "something went wrong" } as any), "#node", "#error")).toBe("#error");
        });
    });

    describe("invocation steps (with headerClass)", () => {
        it("returns the matching state color for an active header-* class", () => {
            const step = makeGraphStep({ headerClass: { "node-header-invocation": true, "header-ok": true } } as any);
            expect(getStepColor(step, "#node", "#error")).toBe(STATE_COLORS["--state-color-ok"]);
        });

        it("returns the error state color for header-error", () => {
            const step = makeGraphStep({
                headerClass: { "node-header-invocation": true, "header-error": true },
            } as any);
            expect(getStepColor(step, "#node", "#error")).toBe(STATE_COLORS["--state-color-error"]);
        });

        it("ignores inactive header-* classes and falls back to the undefined color", () => {
            const step = makeGraphStep({
                headerClass: { "node-header-invocation": true, "header-undefined": false },
            } as any);
            expect(getStepColor(step, "#node", "#error")).toBe(STATE_COLORS["--state-color-undefined"]);
        });

        it("falls back to undefined color when headerClass has no header-* keys", () => {
            const step = makeGraphStep({ headerClass: { "node-header-invocation": true } } as any);
            expect(getStepColor(step, "#node", "#error")).toBe(STATE_COLORS["--state-color-undefined"]);
        });

        it("falls back to nodeColor when undefined color is also unset", () => {
            initStateColors(makeMockStyle({}));
            const step = makeGraphStep({ headerClass: { "node-header-invocation": true } } as any);
            expect(getStepColor(step, "#node", "#error")).toBe("#node");
        });
    });
});

describe("drawSteps", () => {
    it("fills each step rect using the provided color", () => {
        const ctx = makeCtx();
        const steps = [makeStep({ id: 1, position: { left: 5, top: 10 } } as any)];
        const stateStore = makeStateStore({ 1: { width: 100, height: 40 } });

        drawSteps(ctx, steps, "#ff0000", stateStore);

        expect(ctx.fillStyle).toBe("#ff0000");
        expect(ctx.beginPath).toHaveBeenCalled();
        expect(ctx.rect).toHaveBeenCalledWith(5, 10, 100, 40);
        expect(ctx.fill).toHaveBeenCalled();
    });

    it("skips steps with no recorded position", () => {
        const ctx = makeCtx();
        const steps = [makeStep({ id: 99 } as any)];
        const stateStore = makeStateStore({});

        drawSteps(ctx, steps, "#ff0000", stateStore);

        expect(ctx.rect).not.toHaveBeenCalled();
    });
});

describe("drawStepBorders", () => {
    it("strokes each step rect using the provided border color", () => {
        const ctx = makeCtx();
        const steps = [makeStep({ id: 1, position: { left: 5, top: 10 } } as any)];
        const stateStore = makeStateStore({ 1: { width: 100, height: 40 } });

        drawStepBorders(ctx, steps, "#0000ff", stateStore);

        expect(ctx.strokeStyle).toBe("#0000ff");
        expect(ctx.lineWidth).toBe(1);
        expect(ctx.rect).toHaveBeenCalledWith(5, 10, 100, 40);
        expect(ctx.stroke).toHaveBeenCalled();
    });

    it("skips steps with no recorded position", () => {
        const ctx = makeCtx();
        const steps = [makeStep({ id: 99 } as any)];
        const stateStore = makeStateStore({});

        drawStepBorders(ctx, steps, "#0000ff", stateStore);

        expect(ctx.rect).not.toHaveBeenCalled();
    });
});
