import "@/composables/__mocks__/filter";

import { composeStories } from "@storybook/vue3-vite";
import { emittedArg, getLocalVue } from "@tests/vitest/helpers";
import { useStoryMount } from "@tests/vitest/stories";
import { mount } from "@vue/test-utils";
import { describe, expect, it, onTestFinished } from "vitest";

import * as FormSelectionStories from "./FormSelection.stories";

import FormSelect from "./FormSelect.vue";
import FormSelection from "./FormSelection.vue";

const stories = composeStories(FormSelectionStories);
const mountStory = useStoryMount();

// The stories' option labels, in order.
const optionLabels = ["Human (hg38)", "Mouse (mm10)", "Unspecified", "Custom build 99"];

/** Mounts a story, whose harness passes every emitted `input` back as `value`, as a v-model parent does. */
function mountFormSelection(story) {
    return mountStory(story).getComponent(FormSelection);
}

/** vue-multiselect renders its option list only while open, and picking a single option closes it. */
async function openMultiselect(wrapper) {
    if (!wrapper.find(".multiselect__content-wrapper").exists()) {
        await wrapper.find(".multiselect__select").trigger("mousedown");
    }
}

async function listedLabels(wrapper) {
    await openMultiselect(wrapper);
    return wrapper.findAll("[data-option-value]").map((option) => option.text());
}

async function selectedLabels(wrapper) {
    await openMultiselect(wrapper);
    return wrapper.findAll(".multiselect__option--selected").map((option) => option.text());
}

async function clickOption(wrapper, label) {
    await openMultiselect(wrapper);
    const option = wrapper.findAll(".multiselect__option").find((candidate) => candidate.text() === label);
    if (!option) {
        throw new Error(`No option labelled "${label}".`);
    }
    await option.trigger("click");
}

describe("FormSelect", () => {
    describe("single select", () => {
        it("lists the options in order", async () => {
            const wrapper = mountFormSelection(stories.Required);

            expect(await listedLabels(wrapper)).toEqual(optionLabels);
        });

        it("selects the first option when a required select has no value", async () => {
            // A plain mount, without the story's harness, so the select is seen before its parent passes the value back.
            const wrapper = mount(FormSelection, {
                global: getLocalVue(),
                props: stories.Required.args,
            });
            onTestFinished(() => wrapper.unmount());

            expect(emittedArg(wrapper, "input")).toBe("hg38");
            expect(await selectedLabels(wrapper)).toEqual([]);

            await wrapper.setProps({ value: "hg38" });

            expect(await selectedLabels(wrapper)).toEqual(["Human (hg38)"]);
        });

        it("offers and selects 'Nothing selected' while an optional select has no value", async () => {
            const wrapper = mountFormSelection(stories.Optional);

            expect(await listedLabels(wrapper)).toEqual(["Nothing selected", ...optionLabels]);
            expect(await selectedLabels(wrapper)).toEqual(["Nothing selected"]);
            expect(wrapper.emitted("input")).toBeUndefined();
        });

        it("clears an optional select by picking 'Nothing selected'", async () => {
            const wrapper = mountFormSelection(stories.OptionalSelected);
            expect(await selectedLabels(wrapper)).toEqual(["Human (hg38)"]);

            await clickOption(wrapper, "Nothing selected");

            expect(emittedArg(wrapper, "input")).toBe(null);
            expect(await selectedLabels(wrapper)).toEqual(["Nothing selected"]);
        });
    });

    describe("multi-select", () => {
        it("emits null when a required multi-select is fully cleared", async () => {
            const wrapper = mountFormSelection(stories.MultipleRequired);
            expect(await listedLabels(wrapper)).toEqual(optionLabels);
            expect(await selectedLabels(wrapper)).toEqual(["Human (hg38)"]);

            await clickOption(wrapper, "Human (hg38)");

            expect(emittedArg(wrapper, "input")).toBe(null);
        });

        it("does not offer 'Nothing selected' in an optional multi-select", async () => {
            const wrapper = mountFormSelection(stories.MultipleOptional);

            expect(await listedLabels(wrapper)).toEqual(optionLabels);
            expect(await selectedLabels(wrapper)).toEqual(["Human (hg38)", "Unspecified", "Custom build 99"]);
        });

        it("emits the remaining values as options are deselected, null once none are left, and reselects", async () => {
            const wrapper = mountFormSelection(stories.MultipleOptional);
            expect(await selectedLabels(wrapper)).toEqual(["Human (hg38)", "Unspecified", "Custom build 99"]);

            await clickOption(wrapper, "Human (hg38)");
            expect(emittedArg(wrapper, "input")).toEqual(["", 99]);

            await clickOption(wrapper, "Unspecified");
            expect(emittedArg(wrapper, "input", 1)).toEqual([99]);

            await clickOption(wrapper, "Custom build 99");
            expect(emittedArg(wrapper, "input", 2)).toBe(null);

            await clickOption(wrapper, "Human (hg38)");
            expect(emittedArg(wrapper, "input", 3)).toEqual(["hg38"]);
        });
    });
});

describe("FormSelect accessible names", () => {
    it("does not name the search input after its id", () => {
        const wrapper = mountFormSelection(stories.Required);
        const input = wrapper.find("input.multiselect__input");
        expect(input.exists()).toBe(true);
        expect(input.attributes("aria-label")).toBeUndefined();
    });

    it("gives each instance its own default id", () => {
        // FormSelection passes its own id, so mount FormSelect itself to reach the default
        const options = [{ label: "label_1", value: "value_1" }];
        const ids = [0, 1].map(() => {
            const wrapper = mount(FormSelect, { global: getLocalVue(true), props: { options } });
            onTestFinished(() => wrapper.unmount());
            return wrapper.find("input.multiselect__input").attributes("id");
        });
        expect(ids[0]).toMatch(/^form-select-/);
        expect(ids[0]).not.toBe(ids[1]);
    });
});
