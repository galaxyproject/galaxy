import { composeStories } from "@storybook/vue3-vite";
import { emittedArg, getLocalVue } from "@tests/vitest/helpers";
import { useStoryMount } from "@tests/vitest/stories";
import { mount } from "@vue/test-utils";
import { describe, expect, it, onTestFinished } from "vitest";

import * as FormOptionalTextStories from "./FormOptionalText.stories";

import FormOptionalText from "./FormOptionalText.vue";

const stories = composeStories(FormOptionalTextStories);
const mountStory = useStoryMount();

const SELECTORS = {
    SWITCH: "input[type='checkbox']",
    TEXT_INPUT: "input[type='text']",
};

/** Mounts a story, whose harness passes every emitted `input` back as `value`, as a v-model parent does. */
function mountFormOptionalText(story) {
    return mountStory(story).getComponent(FormOptionalText);
}

describe("FormOptionalText", () => {
    it("names an optional input and keeps its label associated after toggling", async () => {
        const wrapper = mountFormOptionalText(stories.WithValue);
        const label = wrapper.find("label.sr-only");
        expect(label.text()).toBe("Optional value");
        expect(label.attributes("for")).toBe(wrapper.find(SELECTORS.TEXT_INPUT).attributes("id"));
        // the story's harness passes the emitted null, then "", back as the value
        await wrapper.find(SELECTORS.SWITCH).setValue(false);
        expect(wrapper.find("label.sr-only").exists()).toBe(false);
        await wrapper.find(SELECTORS.SWITCH).setValue(true);
        expect(wrapper.find("label.sr-only").attributes("for")).toBe(label.attributes("for"));
    });

    it("renders the optional toggle as a switch on the ui-switch label", async () => {
        const wrapper = mountFormOptionalText(stories.Unset);
        const toggle = wrapper.find("label.ui-switch");
        expect(toggle.text()).toBe("Set value for this optional select field?");
        expect(toggle.find("input[type=checkbox]").attributes("role")).toBe("switch");
    });

    it("switches on and shows an existing value", () => {
        const wrapper = mountFormOptionalText(stories.WithValue);

        expect(wrapper.find(SELECTORS.SWITCH).element.checked).toBe(true);
        expect(wrapper.find(SELECTORS.TEXT_INPUT).element.value).toBe(stories.WithValue.args.value);
    });

    it("emits null when switched off and an empty string when switched back on", async () => {
        const wrapper = mountFormOptionalText(stories.WithValue);
        const toggle = wrapper.find(SELECTORS.SWITCH);

        await toggle.setValue(false);
        expect(emittedArg(wrapper, "input", 0)).toBeNull();
        expect(toggle.element.checked).toBe(false);
        expect(wrapper.find(SELECTORS.TEXT_INPUT).exists()).toBe(false);

        await toggle.setValue(true);
        expect(emittedArg(wrapper, "input", 1)).toBe("");
        expect(toggle.element.checked).toBe(true);
        expect(wrapper.find(SELECTORS.TEXT_INPUT).element.value).toBe("");
    });

    it("starts switched off for a null value", () => {
        const wrapper = mountFormOptionalText(stories.Unset);

        expect(wrapper.find(SELECTORS.SWITCH).element.checked).toBe(false);
        expect(wrapper.find(SELECTORS.TEXT_INPUT).exists()).toBe(false);
    });

    it("switches on once its parent sets a value", async () => {
        // A plain mount, as a story can't change a live mount's props.
        const wrapper = mount(FormOptionalText, {
            global: getLocalVue(),
            props: stories.Unset.args,
        });
        onTestFinished(() => wrapper.unmount());
        const toggle = wrapper.find(SELECTORS.SWITCH);
        expect(toggle.element.checked).toBe(false);
        expect(wrapper.find(SELECTORS.TEXT_INPUT).exists()).toBe(false);

        await wrapper.setProps({ value: "" });

        expect(toggle.element.checked).toBe(true);
        expect(wrapper.find(SELECTORS.TEXT_INPUT).exists()).toBe(true);
    });
});
