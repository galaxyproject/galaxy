import { composeStories } from "@storybook/vue3-vite";
import { emittedArg } from "@tests/vitest/helpers";
import { useStoryMount } from "@tests/vitest/stories";
import { describe, expect, it } from "vitest";

import * as FormDrilldownStories from "./FormDrilldown.stories";

import FormDrilldown from "./FormDrilldown.vue";

const stories = composeStories(FormDrilldownStories);
const mountStory = useStoryMount();

/** Mounts a story, whose harness passes every emitted `input` back as `value`, as a v-model parent does. */
function mountDrilldown(story, props = {}) {
    return mountStory(story, { props }).getComponent(FormDrilldown);
}

async function toggle(wrapper, name, checked) {
    await wrapper.get(`#drilldown-option-${name}`).setValue(checked);
}

describe("FormDrilldown", () => {
    it("submits only the chosen option when it has descendants", async () => {
        const wrapper = mountDrilldown(stories.NothingSelected);
        await toggle(wrapper, "Bacteria", true);

        expect(emittedArg(wrapper, "input")).toEqual(["bacteria"]);
    });

    it("keeps other selections when adding one", async () => {
        const wrapper = mountDrilldown(stories.NestedOptionSelected);
        await toggle(wrapper, "Proteobacteria", true);

        expect(emittedArg(wrapper, "input")).toEqual(["euryarchaeota", "proteobacteria"]);
    });

    it("removes only the deselected option, keeping its selected descendants", async () => {
        const wrapper = mountDrilldown(stories.ParentAndChildSelected);
        await toggle(wrapper, "Bacteria", false);

        expect(emittedArg(wrapper, "input")).toEqual(["firmicutes"]);
    });

    it("emits the chosen value alone when not multiple", async () => {
        const wrapper = mountDrilldown(stories.SingleChoice);
        await toggle(wrapper, "Escherichia", true);

        expect(emittedArg(wrapper, "input")).toBe("escherichia");
    });

    it("checks the options in the current value", () => {
        const wrapper = mountDrilldown(stories.NothingSelected, { value: ["firmicutes", "euryarchaeota"] });
        expect(wrapper.get("#drilldown-option-Firmicutes").element.checked).toBe(true);
        expect(wrapper.get("#drilldown-option-Euryarchaeota").element.checked).toBe(true);
        expect(wrapper.get("#drilldown-option-Proteobacteria").element.checked).toBe(false);
    });

    it("selects every value from select all", async () => {
        const wrapper = mountDrilldown(stories.NothingSelected);
        await wrapper.get(".select-all-checkbox input").setValue(true);
        expect([...emittedArg(wrapper, "input")].sort()).toEqual([
            "archaea",
            "bacteria",
            "escherichia",
            "euryarchaeota",
            "firmicutes",
            "proteobacteria",
        ]);
    });

    it("clears the value from select all", async () => {
        const wrapper = mountDrilldown(stories.NothingSelected, {
            value: ["bacteria", "firmicutes", "proteobacteria", "escherichia", "archaea", "euryarchaeota"],
        });
        const selectAll = wrapper.get(".select-all-checkbox input");
        expect(selectAll.element.checked).toBe(true);
        await selectAll.setValue(false);
        expect(emittedArg(wrapper, "input")).toBeNull();
    });

    it("marks select all as partly checked when some values are selected", () => {
        const wrapper = mountDrilldown(stories.NothingSelected, { value: ["firmicutes"] });
        expect(wrapper.get(".select-all-checkbox input").element.indeterminate).toBe(true);
    });

    it("gives single-select radios one shared name for keyboard navigation", () => {
        const wrapper = mountDrilldown(stories.SingleChoice, { value: "proteobacteria" });
        const radios = wrapper.findAll("input[type=radio]");
        expect(radios.length).toBe(6);
        const names = new Set(radios.map((radio) => radio.attributes("name")));
        expect(names.size).toBe(1);
        expect([...names][0]).toBeTruthy();
        expect(wrapper.get("#drilldown-option-Proteobacteria").element.checked).toBe(true);
        expect(wrapper.find(".select-all-checkbox").exists()).toBe(false);
    });

    it("keeps the radios of two drilldowns with the same id in separate groups", async () => {
        const mountSingle = (value) =>
            mountStory(stories.SingleChoice, { props: { value }, attachTo: document.body }).getComponent(FormDrilldown);
        const first = mountSingle("bacteria");
        const second = mountSingle("archaea");
        const firstName = first.get("input[type=radio]").attributes("name");
        const secondName = second.get("input[type=radio]").attributes("name");
        expect(firstName).toBeTruthy();
        expect(firstName).not.toBe(secondName);
        await first.get("#drilldown-option-Firmicutes").setValue(true);
        expect(second.get("#drilldown-option-Archaea").element.checked).toBe(true);
    });
});
