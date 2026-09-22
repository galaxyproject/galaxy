import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import CustomToolEditorWorkspace from "./CustomToolEditorWorkspace.vue";
import DraggableSeparator from "@/components/Common/DraggableSeparator.vue";

describe("CustomToolEditorWorkspace", () => {
    function mountWorkspace() {
        return mount(CustomToolEditorWorkspace as object, {
            propsData: {
                documentationVisible: false,
            },
            slots: {
                editor: '<textarea data-description="tool yaml editor" />',
                documentation: '<article data-description="tool documentation" />',
            },
        });
    }

    it("starts with documentation hidden", () => {
        const wrapper = mountWorkspace();

        expect(wrapper.find('[data-description="tool yaml editor"]').isVisible()).toBe(true);
        expect(wrapper.find('[data-description="tool documentation"]').exists()).toBe(false);
    });

    it("shows the editor and documentation side by side", async () => {
        const wrapper = mountWorkspace();

        await wrapper.setProps({ documentationVisible: true });

        expect(wrapper.find('[data-description="tool yaml editor"]').isVisible()).toBe(true);
        expect(wrapper.find('[data-description="tool documentation"]').isVisible()).toBe(true);
    });

    it("expands documentation across the full workspace", async () => {
        const wrapper = mountWorkspace();
        await wrapper.setProps({ documentationVisible: true });

        await wrapper.find('[data-description="toggle expanded documentation"]').trigger("click");

        expect(wrapper.find('[data-description="tool yaml editor"]').isVisible()).toBe(false);
        expect(wrapper.find('[data-description="tool documentation"]').isVisible()).toBe(true);
        expect(wrapper.find("#custom-tool-documentation-panel").classes()).toContain("documentation-only");
    });

    it("keeps both views mounted and restores split view after reopening documentation", async () => {
        const wrapper = mountWorkspace();
        const editor = wrapper.find('[data-description="tool yaml editor"]');

        await wrapper.setProps({ documentationVisible: true });
        const documentation = wrapper.find('[data-description="tool documentation"]');
        await wrapper.find('[data-description="toggle expanded documentation"]').trigger("click");
        await wrapper.setProps({ documentationVisible: false });
        await wrapper.setProps({ documentationVisible: true });

        expect(wrapper.find('[data-description="tool yaml editor"]').element).toBe(editor.element);
        expect(wrapper.find('[data-description="tool documentation"]').element).toBe(documentation.element);
        expect(editor.isVisible()).toBe(true);
        expect(documentation.isVisible()).toBe(true);
    });

    it("resizes documentation from the drag separator", async () => {
        const wrapper = mountWorkspace();
        await wrapper.setProps({ documentationVisible: true });

        wrapper.findComponent(DraggableSeparator).vm.$emit("positionChanged", 620);
        await wrapper.vm.$nextTick();

        expect(wrapper.find("#custom-tool-documentation-panel").attributes("style")).toContain("--width: 620px");
    });
});
