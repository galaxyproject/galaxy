import { beforeEach, describe, expect, it } from "vitest";

import { setupTestPinia } from "./testUtils";
import { type InputCatcherEvent, useWorkflowEditorToolbarStore } from "./workflowEditorToolbarStore";

describe("workflowEditorToolbarStore", () => {
    beforeEach(setupTestPinia);

    it("delivers input catcher events to matching listeners in emission order", () => {
        const toolbarStore = useWorkflowEditorToolbarStore("mock-workflow-id");

        const receivedEvents: InputCatcherEvent[] = [];

        for (const eventType of ["pointerdown", "pointerup", "pointermove", "temporarilyDisabled"] as const) {
            toolbarStore.onInputCatcherEvent(eventType, (event) => receivedEvents.push(event));
        }

        toolbarStore.emitInputCatcherEvent("pointerdown", { type: "pointerdown", position: [100, 200] });
        expect(receivedEvents).toHaveLength(1);
        expect(receivedEvents[0]).toEqual({ type: "pointerdown", position: [100, 200] });

        toolbarStore.emitInputCatcherEvent("pointermove", { type: "pointermove", position: [0, 0] });
        toolbarStore.emitInputCatcherEvent("pointerup", { type: "pointerup", position: [0, 0] });
        toolbarStore.emitInputCatcherEvent("temporarilyDisabled", { type: "temporarilyDisabled", position: [0, 0] });

        expect(receivedEvents[1]).toEqual({ type: "pointermove", position: [0, 0] });
        expect(receivedEvents[2]).toEqual({ type: "pointerup", position: [0, 0] });
        expect(receivedEvents[3]).toEqual({ type: "temporarilyDisabled", position: [0, 0] });
    });
});
