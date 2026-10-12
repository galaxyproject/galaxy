import { enableAutoUnmount, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, onTestFinished } from "vitest";

import CustomToolEditorWorkspace from "./CustomToolEditorWorkspace.vue";
import DraggableSeparator from "@/components/Common/DraggableSeparator.vue";

describe("CustomToolEditorWorkspace", () => {
    enableAutoUnmount(afterEach);
    afterEach(async () => {
        // Finish the drag separator's current frame while its owned wrapper is still mounted.
        await new Promise((resolve) => window.requestAnimationFrame(resolve));
    });

    function mountWorkspace() {
        const target = document.createElement("div");
        document.body.appendChild(target);
        onTestFinished(() => target.remove());
        return mount(CustomToolEditorWorkspace, {
            props: {
                documentationVisible: false,
            },
            slots: {
                editor: '<textarea data-description="tool yaml editor" />',
                documentation: '<article data-description="tool documentation" />',
            },
            // happy-dom only resolves getComputedStyle() (what isVisible() reads) for
            // elements attached to the document, so use an owned attachment target.
            attachTo: target,
        });
    }

    it("starts with documentation hidden", () => {
        const wrapper = mountWorkspace();

        expect(wrapper.get('[data-description="tool yaml editor"]').isVisible()).toBe(true);
        expect(wrapper.find('[data-description="tool documentation"]').exists()).toBe(false);
    });

    it("shows the editor and documentation side by side", async () => {
        const wrapper = mountWorkspace();

        await wrapper.setProps({ documentationVisible: true });

        expect(wrapper.get('[data-description="tool yaml editor"]').isVisible()).toBe(true);
        expect(wrapper.get('[data-description="tool documentation"]').isVisible()).toBe(true);
    });

    it("expands documentation across the full workspace", async () => {
        const wrapper = mountWorkspace();
        await wrapper.setProps({ documentationVisible: true });

        await wrapper.get('[data-description="toggle expanded documentation"]').trigger("click");

        expect(wrapper.get('[data-description="tool yaml editor"]').isVisible()).toBe(false);
        expect(wrapper.get('[data-description="tool documentation"]').isVisible()).toBe(true);
        expect(wrapper.get("#custom-tool-documentation-panel").classes()).toContain("documentation-only");
    });

    it("keeps both views mounted and restores split view after reopening documentation", async () => {
        const wrapper = mountWorkspace();
        const editor = wrapper.get('[data-description="tool yaml editor"]');

        await wrapper.setProps({ documentationVisible: true });
        const documentation = wrapper.get('[data-description="tool documentation"]');
        await wrapper.get('[data-description="toggle expanded documentation"]').trigger("click");
        await wrapper.setProps({ documentationVisible: false });
        await wrapper.setProps({ documentationVisible: true });

        expect(wrapper.get('[data-description="tool yaml editor"]').element).toBe(editor.element);
        expect(wrapper.get('[data-description="tool documentation"]').element).toBe(documentation.element);
        expect(editor.isVisible()).toBe(true);
        expect(documentation.isVisible()).toBe(true);
    });

    it("resizes documentation from the drag separator", async () => {
        const wrapper = mountWorkspace();
        await wrapper.setProps({ documentationVisible: true });

        wrapper.getComponent(DraggableSeparator).vm.$emit("positionChanged", 620);
        await wrapper.vm.$nextTick();

        expect(wrapper.get("#custom-tool-documentation-panel").attributes("style")).toContain("--width: 620px");
    });
});
