import { composeStories } from "@storybook/vue3-vite";
import { emittedArg } from "@tests/vitest/helpers";
import { useStoryMount } from "@tests/vitest/stories";
import { describe, expect, it } from "vitest";

import * as FormDrilldownStories from "./FormDrilldown.stories";

import FormDrilldown from "./FormDrilldown.vue";

const stories = composeStories(FormDrilldownStories);
const mountStory = useStoryMount();

/** Mounts a story, whose harness passes every emitted `input` back as `value`, as a v-model parent does. */
function mountDrilldown(story) {
    return mountStory(story).getComponent(FormDrilldown);
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
});
