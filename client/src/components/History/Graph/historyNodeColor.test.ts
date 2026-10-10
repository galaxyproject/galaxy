import { afterAll, beforeAll, describe, expect, it, vi } from "vitest";

import type { HistoryGraphNode, HistoryGraphNodeData } from "./historyGraphMapper";
import { historyNodeColor } from "./historyNodeColor";

/** The `--state-color-*` custom properties as `getComputedStyle` reports them, whitespace included. */
const STATE_COLOR_PROPERTIES: Record<string, string> = {
    "--state-color-ok": " #00ff00 ",
    "--state-color-error": "#ff0000",
    "--state-color-running": "#0000ff",
    "--state-color-failed-metadata": "#ff00ff",
};

function graphNode(data: Partial<HistoryGraphNodeData>): HistoryGraphNode {
    return {
        id: "x",
        x: 0,
        y: 0,
        width: 0,
        height: 0,
        label: "",
        icon: {} as HistoryGraphNode["icon"],
        data: {
            src: "hda",
            typeLabel: "",
            itemId: "",
            toolId: null,
            executionIndex: undefined,
            inputCount: 0,
            outputCount: 0,
            state: null,
            stateText: null,
            stateDisplayName: null,
            stateSpin: false,
            ...data,
        },
    };
}

describe("historyNodeColor", () => {
    // Each state's color is cached for the module's lifetime, so every test shares one set of properties.
    beforeAll(() => {
        vi.spyOn(window, "getComputedStyle").mockReturnValue({
            getPropertyValue: (name: string) => STATE_COLOR_PROPERTIES[name] ?? "",
        } as CSSStyleDeclaration);
    });

    afterAll(() => {
        vi.restoreAllMocks();
    });

    it.each([
        { src: "hda", state: "ok", expected: "#00ff00" },
        { src: "hdca", state: "error", expected: "#ff0000" },
        { src: "hda", state: "running", expected: "#0000ff" },
    ] as const)("colors a $src node in state $state with its trimmed state color", ({ src, state, expected }) => {
        expect(historyNodeColor(graphNode({ src, state }))).toBe(expected);
    });

    it("reads underscored states from dashed custom properties", () => {
        expect(historyNodeColor(graphNode({ src: "hda", state: "failed_metadata" }))).toBe("#ff00ff");
    });

    it.each(["ok", undefined])("leaves tool_request nodes uncolored in state %s", (state) => {
        expect(historyNodeColor(graphNode({ src: "tool_request", state }))).toBeNull();
    });

    it.each([null, undefined])("leaves nodes uncolored when the state is %s", (state) => {
        expect(historyNodeColor(graphNode({ src: "hda", state }))).toBeNull();
    });

    it("leaves nodes uncolored when their state has no custom property", () => {
        expect(historyNodeColor(graphNode({ src: "hda", state: "unknown_state" }))).toBeNull();
    });
});
