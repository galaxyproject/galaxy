import { getLocalVue } from "@tests/vitest/helpers";
import { shallowMount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";

import EditorSplitView from "./EditorSplitView.vue";

const localVue = getLocalVue();

function mountComponent(propsData = {}) {
    return shallowMount(EditorSplitView as object, {
        localVue,
        propsData,
        slots: {
            editor: '<div class="test-editor">Editor</div>',
            chat: '<div class="test-chat">Chat</div>',
        },
    });
}

describe("EditorSplitView", () => {
    it("renders split view container", () => {
        const wrapper = mountComponent();
        expect(wrapper.find('[data-description="editor split view"]').exists()).toBe(true);
    });

    it("renders editor slot", () => {
        const wrapper = mountComponent();
        expect(wrapper.find(".test-editor").exists()).toBe(true);
    });

    it("renders chat slot", () => {
        const wrapper = mountComponent();
        expect(wrapper.find(".test-chat").exists()).toBe(true);
    });

    it("renders resize handle", () => {
        const wrapper = mountComponent();
        expect(wrapper.find('[data-description="split resize handle"]').exists()).toBe(true);
    });

    it("has default 60% split", () => {
        const wrapper = mountComponent();
        const editorPane = wrapper.find(".editor-pane");
        expect(editorPane.attributes("style")).toContain("flex-basis: 60%");
    });

    it("chat pane has complementary width", () => {
        const wrapper = mountComponent();
        const chatPane = wrapper.find(".chat-pane");
        expect(chatPane.attributes("style")).toContain("flex-basis: 40%");
    });

    it("adds is-dragging class on mousedown", async () => {
        const wrapper = mountComponent();
        const handle = wrapper.find('[data-description="split resize handle"]');
        await handle.trigger("mousedown");
        expect(wrapper.find(".editor-split-view").classes()).toContain("is-dragging");
    });
});
