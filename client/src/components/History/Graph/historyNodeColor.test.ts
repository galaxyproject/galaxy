import { beforeEach, describe, expect, it, vi } from "vitest";

import type { HistoryGraphNode, HistoryGraphNodeData } from "./historyGraphMapper";
import { historyNodeColor } from "./historyNodeColor";

function node(data: Partial<HistoryGraphNodeData>): HistoryGraphNode {
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
    beforeEach(() => {
        // jsdom's getComputedStyle returns "" by default, but the lazy cache
        // would store it; reset via dynamic re-import would be heavy. Spy in
        // each test instead so the state→color map is controllable.
        vi.spyOn(window, "getComputedStyle").mockImplementation(
            () =>
                ({
                    getPropertyValue: (name: string) =>
                        name === "--state-color-ok"
                            ? " #00ff00 "
                            : name === "--state-color-error"
                              ? "#ff0000"
                              : name === "--state-color-running"
                                ? "#0000ff"
                                : "",
                }) as CSSStyleDeclaration,
        );
    });

    it("returns null for tool_request nodes regardless of state", () => {
        expect(historyNodeColor(node({ src: "tool_request", state: "ok" }))).toBeNull();
        expect(historyNodeColor(node({ src: "tool_request", state: undefined }))).toBeNull();
    });

    it("returns the trimmed state color for dataset/collection nodes with a known state", () => {
        expect(historyNodeColor(node({ src: "hda", state: "ok" }))).toBe("#00ff00");
        expect(historyNodeColor(node({ src: "hdca", state: "error" }))).toBe("#ff0000");
        expect(historyNodeColor(node({ src: "hda", state: "running" }))).toBe("#0000ff");
    });

    it("returns null when the state is missing", () => {
        expect(historyNodeColor(node({ src: "hda", state: null }))).toBeNull();
        expect(historyNodeColor(node({ src: "hda", state: undefined }))).toBeNull();
    });

    it("returns null when the CSS variable is not defined", () => {
        expect(historyNodeColor(node({ src: "hda", state: "unknown_state" }))).toBeNull();
    });
});
