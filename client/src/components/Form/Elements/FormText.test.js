import { composeStories } from "@storybook/vue3-vite";
import { getLocalVue } from "@tests/vitest/helpers";
import { useStoryMount } from "@tests/vitest/stories";
import { mount } from "@vue/test-utils";
import { BFormInput } from "bootstrap-vue";
import { describe, expect, it, onTestFinished } from "vitest";

import * as FormTextStories from "./FormText.stories";

import FormText from "./FormText.vue";

const stories = composeStories(FormTextStories);
const mountStory = useStoryMount();

/** Mounts a story, whose harness passes every emitted `input` back as `value`, as a v-model parent does. */
function mountFormText(story, props) {
    return mountStory(story, { props }).getComponent(FormText);
}

/** A plain mount, as a story can't change a live mount's props. */
function mountLiveFormText(props) {
    const wrapper = mount(FormText, { global: getLocalVue(), props });
    onTestFinished(() => wrapper.unmount());
    return wrapper;
}

describe("FormText", () => {
    it("renders text and password inputs with a text fallback", () => {
        expect(mountFormText(stories.Text).find("input[type='text']").exists()).toBe(true);
        expect(mountFormText(stories.Password).find("input[type='password']").exists()).toBe(true);
        const fallback = mountFormText(stories.WorkflowDataColumn);
        expect(fallback.find("input[type='text']").exists()).toBe(true);
        // bootstrap-vue falls back to text on its own, so check what FormText asks for
        expect(fallback.getComponent(BFormInput).props("type")).toBe("text");
    });

    it("follows a changed type", async () => {
        const wrapper = mountLiveFormText(stories.Text.args);
        const textInput = wrapper.find("input[type='text']");
        expect(textInput.exists()).toBe(true);
        await wrapper.setProps({ type: "password" });
        const passwordInput = wrapper.find("input[type='password']");
        expect(passwordInput.exists()).toBe(true);
        await wrapper.setProps({ type: stories.WorkflowDataColumn.args.type });
        const fallbackInput = wrapper.find("input[type='text']");
        expect(fallbackInput.exists()).toBe(true);
        expect(wrapper.getComponent(BFormInput).props("type")).toBe("text");
    });

    it("renders a textarea for area and multiple inputs", () => {
        expect(mountFormText(stories.TextArea).find("textarea").exists()).toBe(true);
        expect(mountFormText(stories.MultipleValues).find("textarea").exists()).toBe(true);
    });

    it("keeps a textarea when area gives way to multiple", async () => {
        const wrapper = mountLiveFormText(stories.TextArea.args);
        const areaInput = wrapper.find("textarea");
        expect(areaInput.exists()).toBe(true);
        await wrapper.setProps({ area: false, multiple: true });
        const multipleInput = wrapper.find("textarea");
        expect(multipleInput.exists()).toBe(true);
    });

    it("renders and links a datalist with options", () => {
        const wrapper = mountFormText(stories.WithSuggestions);
        expect(wrapper.find("datalist").exists()).toBe(true);
        expect(wrapper.find("option").exists()).toBe(true);
        expect(wrapper.find("[list='adapter-datalist']").exists()).toBe(true);
        const options = wrapper.findAll("datalist#adapter-datalist option");
        expect(options.map((option) => [option.attributes("label"), option.attributes("value")])).toEqual(
            stories.WithSuggestions.args.datalist.map(({ label, value }) => [label, value]),
        );
    });

    it("omits the datalist and its link without options", () => {
        for (const datalist of [undefined, []]) {
            const wrapper = mountFormText(stories.WithSuggestions, { id: "section|text-input", datalist });
            expect(wrapper.find("datalist").exists()).toBe(false);
            expect(wrapper.find("[list]").exists()).toBe(false);
        }
    });

    it("applies text color, border color and custom class props", () => {
        expect(mountFormText(stories.Text).get("input").element.style.color).toBeFalsy();
        const input = mountFormText(stories.WorkflowParameter).get("input");
        expect(input.element.style.color).toBe("hsl( 100, 70%, 30% )");
        expect(input.element.style.borderColor).toBe("hsl( 100, 70%, 30% )");
        expect(input.element.classList).toContain("ui-input-linked");
    });

    it("restyles the same input when color and class change", async () => {
        const wrapper = mountLiveFormText(stories.Text.args);
        const input = wrapper.get("input");
        expect(input.element.style.color).toBeFalsy();
        await wrapper.setProps({ color: stories.WorkflowParameter.args.color });
        expect(input.element.style.color).toBe("hsl( 100, 70%, 30% )");
        expect(input.element.style.borderColor).toBe("hsl( 100, 70%, 30% )");
        await wrapper.setProps({ cls: stories.WorkflowParameter.args.cls });
        expect(input.element.classList).toContain("ui-input-linked");
    });

    it("renders a string value", () => {
        const input = mountFormText(stories.Text).get("input");
        expect(input.element.value).toEqual("wild_type_rep1");
    });

    it("renders the first array value and joins multiple values with newlines", () => {
        const input = mountFormText(stories.MultipleValues, { multiple: false }).get("input");
        expect(input.element.value).toEqual("wild_type_rep1");
        const textarea = mountFormText(stories.MultipleValues).get("textarea");
        expect(textarea.element.value).toEqual("wild_type_rep1\nwild_type_rep2\nknockout_rep1");
    });

    it("joins an array value once multiple is set", async () => {
        const wrapper = mountLiveFormText({ ...stories.MultipleValues.args, multiple: false });
        const input = wrapper.get("input");
        expect(input.element.value).toEqual("wild_type_rep1");
        await wrapper.setProps({ multiple: true });
        const textarea = wrapper.get("textarea");
        expect(textarea.element.value).toEqual("wild_type_rep1\nwild_type_rep2\nknockout_rep1");
    });

    it("renders an empty array as an empty string", () => {
        const input = mountFormText(stories.Text, { value: [] }).get("input");
        expect(input.element.value).toEqual("");
    });
});
