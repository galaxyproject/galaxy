import { composeStories } from "@storybook/vue3-vite";
import { useStoryMount } from "@tests/vitest/stories";
import { enableAutoUnmount, mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, onTestFinished } from "vitest";

import * as CustomToolEditorWorkspaceStories from "./CustomToolEditorWorkspace.stories";

import DraggableSeparator from "@/components/Common/DraggableSeparator.vue";

const stories = composeStories(CustomToolEditorWorkspaceStories);

describe("CustomToolEditorWorkspace", () => {
    const mountStory = useStoryMount();
    enableAutoUnmount(afterEach);
    afterEach(async () => {
        // Finish the drag separator's current frame while its owned wrapper is still mounted.
        await new Promise((resolve) => window.requestAnimationFrame(resolve));
    });

    function ownedTarget() {
        const target = document.createElement("div");
        document.body.appendChild(target);
        onTestFinished(() => target.remove());
        return target;
    }

    function mountWorkspace() {
        return mount(CustomToolEditorWorkspaceStories.WorkspaceWithSlots, {
            props: CustomToolEditorWorkspaceStories.default.args,
            attachTo: ownedTarget(),
        });
    }

    it("starts with documentation hidden", () => {
        const wrapper = mountStory(stories.EditorOnly, { attachTo: ownedTarget() });

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
