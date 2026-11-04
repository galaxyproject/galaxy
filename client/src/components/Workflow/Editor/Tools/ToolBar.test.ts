import { getLocalVue, withPlugins } from "@tests/vitest/helpers";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { describe, expect, it } from "vitest";

import { useWorkflowEditorToolbarStore } from "@/stores/workflowEditorToolbarStore";

import ToolBar from "./ToolBar.vue";

const WORKFLOW_ID = "toolbar-test-workflow";

function mountToolBar() {
    const pinia = createPinia();
    setActivePinia(pinia);
    const toolbarStore = useWorkflowEditorToolbarStore(WORKFLOW_ID);
    toolbarStore.toolbarVisible = true;
    const wrapper = mount(ToolBar as object, {
        global: { ...withPlugins(getLocalVue(), pinia), provide: { workflowId: WORKFLOW_ID } },
    });
    return { wrapper, toolbarStore };
}

function rangeInput(wrapper: ReturnType<typeof mountToolBar>["wrapper"], option: string) {
    const input = wrapper.get(`[data-option='${option}']`);
    expect(input.element.tagName).toBe("INPUT");
    expect(input.classes()).toContain("g-form-input");
    expect(input.attributes("type")).toBe("range");
    return input;
}

describe("ToolBar", () => {
    it("sets the snapping distance from its range", async () => {
        const { wrapper, toolbarStore } = mountToolBar();
        toolbarStore.snapActive = true;
        await wrapper.vm.$nextTick();
        const input = rangeInput(wrapper, "snapping-distance");
        expect((input.element as HTMLInputElement).value).toBe("1");
        await input.setValue("3");
        expect(toolbarStore.snapDistance).toBe(50);
        expect(wrapper.text()).toContain("50 pixels");
    });

    it("sets the text comment size from its range", async () => {
        const { wrapper, toolbarStore } = mountToolBar();
        toolbarStore.currentTool = "textComment";
        await wrapper.vm.$nextTick();
        const input = rangeInput(wrapper, "font-size");
        expect((input.element as HTMLInputElement).value).toBe("2");
        await input.setValue("4");
        expect(toolbarStore.commentOptions.textSize).toBe(4);
    });

    it("sets the freehand size and smoothing as numbers", async () => {
        const { wrapper, toolbarStore } = mountToolBar();
        toolbarStore.currentTool = "freehandComment";
        await wrapper.vm.$nextTick();

        const thickness = rangeInput(wrapper, "line-thickness");
        expect((thickness.element as HTMLInputElement).value).toBe("5");
        await thickness.setValue("12");
        expect(toolbarStore.commentOptions.lineThickness).toBe(12);
        expect(wrapper.text()).toContain("12 pixels");

        const smoothing = rangeInput(wrapper, "smoothing");
        expect((smoothing.element as HTMLInputElement).value).toBe("2");
        await smoothing.setValue("7");
        expect(toolbarStore.commentOptions.smoothing).toBe(7);
    });
});
