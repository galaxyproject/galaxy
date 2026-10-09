import { beforeEach, describe, expect, it, vi } from "vitest";

import type { GraphStep } from "@/composables/useInvocationGraph";
import { setupTestPinia } from "@/stores/testUtils";
import { useWorkflowStateStore } from "@/stores/workflowEditorStateStore";
import type { Step } from "@/stores/workflowStepStore";

import { createMockStepPosition, createTestStep } from "../test_fixtures";
import { drawStepBorders, drawSteps, getStepColor, initStateColors } from "./canvasDraw";

function makeStyle(vars: Record<string, string>): CSSStyleDeclaration {
    const style = document.createElement("div").style;
    for (const [name, value] of Object.entries(vars)) {
        style.setProperty(name, value);
    }
    return style;
}

function makeStep(overrides: Partial<Step> = {}): Step {
    return { ...createTestStep(0), id: 0, position: { left: 10, top: 20 }, errors: null, ...overrides };
}

function makeGraphStep(overrides: Partial<GraphStep> = {}): GraphStep {
    return { ...makeStep(), state: "uninitialized", jobs: {}, ...overrides };
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

function makeStateStore(positions: Record<number, { width: number; height: number }>) {
    setupTestPinia();
    const store = useWorkflowStateStore("minimap-test");
    for (const [id, { width, height }] of Object.entries(positions)) {
        store.stepPosition[Number(id)] = createMockStepPosition(width, height);
    }
    return store;
}

const MOCK_COLORS = {
    "--state-color-ok": "#ok-color",
    "--state-color-error": "#error-color",
    "--state-color-uninitialized": "#uninitialized-color",
};

describe("initStateColors + getStepColor", () => {
    beforeEach(() => {
        initStateColors(makeStyle(MOCK_COLORS));
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
        it.each<{ name: string; headerClass: Record<string, boolean>; color: string }>([
            {
                name: "active ok state",
                headerClass: { "node-header-invocation": true, "header-ok": true },
                color: MOCK_COLORS["--state-color-ok"],
            },
            {
                name: "active error state",
                headerClass: { "node-header-invocation": true, "header-error": true },
                color: MOCK_COLORS["--state-color-error"],
            },
            {
                name: "inactive state class",
                headerClass: { "node-header-invocation": true, "header-ok": false },
                color: "#node",
            },
            { name: "no state class", headerClass: { "node-header-invocation": true }, color: "#node" },
            {
                name: "active uninitialized state",
                headerClass: { "node-header-invocation": true, "header-uninitialized": true },
                color: MOCK_COLORS["--state-color-uninitialized"],
            },
        ])("uses the expected color for $name", ({ headerClass, color }) => {
            const step = makeGraphStep({ headerClass });
            expect(getStepColor(step, "#node", "#error")).toBe(color);
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
        expect(ctx.beginPath).toHaveBeenCalledTimes(1);
        expect(ctx.rect).toHaveBeenCalledWith(5, 10, 100, 40);
        expect(ctx.fill).toHaveBeenCalledTimes(1);
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
        expect(ctx.stroke).toHaveBeenCalledTimes(1);
    });

    it("skips steps with no recorded position", () => {
        const ctx = makeCtx();
        const steps = [makeStep({ id: 99 })];
        const stateStore = makeStateStore({});

        drawStepBorders(ctx, steps, "#0000ff", stateStore);

        expect(ctx.rect).not.toHaveBeenCalled();
    });
});
