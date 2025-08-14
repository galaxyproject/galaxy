import { createPinia, setActivePinia } from "pinia";

import { type InputCatcherEvent, useWorkflowEditorToolbarStore } from "./workflowEditorToolbarStore";

describe("workflowEditorToolbarStore", () => {
    beforeEach(() => {
        setActivePinia(createPinia());
    });

    it("has an input catcher event bus", () => {
        const toolbarStore = useWorkflowEditorToolbarStore("mock-workflow-id");

        const receivedEvents: InputCatcherEvent[] = [];

        toolbarStore.onInputCatcherEvent("pointerdown", (e) => receivedEvents.push(e));
        toolbarStore.onInputCatcherEvent("pointerup", (e) => receivedEvents.push(e));
        toolbarStore.onInputCatcherEvent("pointermove", (e) => receivedEvents.push(e));
        toolbarStore.onInputCatcherEvent("temporarilyDisabled", (e) => receivedEvents.push(e));

        toolbarStore.emitInputCatcherEvent("pointerdown", { type: "pointerdown", position: [100, 200] });
        expect(receivedEvents.length).toBe(1);
        expect(receivedEvents[0]?.position).toEqual([100, 200]);

        toolbarStore.emitInputCatcherEvent("pointermove", { type: "pointermove", position: [0, 0] });
        toolbarStore.emitInputCatcherEvent("pointerup", { type: "pointerup", position: [0, 0] });
        toolbarStore.emitInputCatcherEvent("temporarilyDisabled", { type: "temporarilyDisabled", position: [0, 0] });

        expect(receivedEvents[1]?.type).toBe("pointermove");
        expect(receivedEvents[2]?.type).toBe("pointerup");
        expect(receivedEvents[3]?.type).toBe("temporarilyDisabled");
    });
});
